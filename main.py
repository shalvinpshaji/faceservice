import time
import cv2
import face_recognition
from datetime import datetime
import numpy as np
from settings import Settings
import pika
from supabase import create_client, Client
import schedule
import os
import threading
from dotenv import load_dotenv

load_dotenv()

room_id = Settings.ROOM_ID

is_running = False

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)


connection = pika.BlockingConnection(pika.ConnectionParameters(Settings.QUEUE_URL))
channel = connection.channel()
print("[x] Created connection to queue")


def push_to_queue(person_id, schedule_id):
    body = f'{person_id}|{schedule_id}'
    print(f"[x] Added to queue {person_id}")
    try:
        channel.basic_publish(exchange='', routing_key='personid|schedule', body=body.encode('utf-8'))
        return True
    except:
        return False


def get_embeddings(course_id):
    data = supabase.table('people_course').select('people_id').eq('course_id', course_id).execute().data
    people_ids = [people['people_id'] for people in data]
    encodings = supabase.table('people').select('*').in_('id', people_ids).execute().data
    mapping = {value['id']: value['encoding'] for value in encodings}
    ordered_map = {'ids': [], 'encodings': []}
    for people_id in mapping:
        encoding = mapping[people_id]
        if encoding:
            ordered_map['ids'].append(people_id)
            ordered_map['encodings'].append(np.fromstring(mapping[people_id], sep=' '))
    print(f"[x] Collected embeddings for students registered for {course_id}, {people_ids}")
    return ordered_map


def start(ordered_map, schedule_id):
    global is_running
    is_running = True
    print("[x] Starting Attendance Time:", datetime.now())
    print("[x] Found one schedule within 15 minutes")

    cap = cv2.VideoCapture(0)
    end_time = time.time() + 15 * 60
    people_id_marked = []
    while time.time() < end_time:
        ret, frame = cap.read()
        frame_rgb = cv2.resize(frame, (0, 0), None, Settings.SCALE, Settings.SCALE)
        frame_rgb = cv2.cvtColor(frame_rgb, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(frame_rgb, model=Settings.MODEL)
        face_encodings = face_recognition.face_encodings(frame_rgb, face_locations)
        for location, encoding in zip(face_locations, face_encodings):
            match = face_recognition.compare_faces(ordered_map['encodings'], encoding, 0.4)
            for index, is_match in enumerate(match):
                person_id = ordered_map['ids'][index]
                if is_match and person_id not in people_id_marked:
                    if push_to_queue(person_id, schedule_id):
                        print(f"[x] Marked attendance for {person_id}")
                        people_id_marked.append(person_id)
                    else:
                        print(f"[x] Error pushing to queue")
                if Settings.SHOW_PREVIEW:
                    y1, x2, y2, x1 = location
                    y1, x2, y2, x1 = int(y1 * Settings.MULTIPLIER), int(x2 * Settings.MULTIPLIER), \
                        int(y2 * Settings.MULTIPLIER), int(x1 * Settings.MULTIPLIER)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        if Settings.SHOW_PREVIEW:
            cv2.imshow("Live Feed", frame)
            if cv2.waitKey(10) == 27:
                break
    is_running = False


def check_for_schedules():
    global is_running
    if is_running:
        print('[x] Skipping check for schedules, Thread busy taking attendance')
        return
    print(f"[x] {time.time()} : Checking for schedules")
    schedules = supabase.table('class_schedule').select('*').eq('room', room_id).execute()
    for each in schedules.data:
        d = each['datetime'].split('+')[0]
        schedule_time = datetime.strptime(d, '%Y-%m-%dT%H:%M:%S')
        delta = schedule_time - datetime.now()
        if 0 < delta.total_seconds() < (15 * 60) and each['scheduled'] != 1:
            print(f"[x] Found a new schedule, starts at {schedule_time}, {each}")
            print("[x] Minutes left to start", delta.total_seconds() // 60)
            ordered_map = get_embeddings(each['course'])
            u = supabase.table('class_schedule').update({'scheduled': 1}).eq('id', each['id']).execute()
            print("[x] Updated schedule status!")
            threading.Timer(delta.total_seconds(), start, kwargs={'ordered_map': ordered_map,
                                                                  'schedule_id': each['id']}).start()
            break


schedule.every(5).seconds.do(check_for_schedules)

while True:
    schedule.run_pending()
    time.sleep(1)
