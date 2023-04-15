from dotenv import load_dotenv
import os

load_dotenv()


class Settings:
    CAMERA: int = 0
    SCALE: float = 0.2
    ENCODING: str = 'encodings.npy'
    MODEL: str = 'hod'
    WAIT_TIME: int = 10
    MULTIPLIER: int = 1/SCALE
    FONT: int = 3
    SUPABASE_URL: str = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY: str = os.environ.get("SUPABASE_KEY")


