from dotenv import load_dotenv
import os

load_dotenv()


class Settings:
    ROOM_ID: int = 1
    CAMERA: int = 0
    SCALE: float = 0.2
    MODEL: str = 'hod'
    WAIT_TIME: int = 10
    MULTIPLIER: int = 1/SCALE
    FONT: int = 3
    SUPABASE_URL: str = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY: str = os.environ.get("SUPABASE_KEY")
    QUEUE_URL: str = "localhost"
    SHOW_PREVIEW: bool = False


