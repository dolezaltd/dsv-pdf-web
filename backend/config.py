"""Konfigurace backendu."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Načtení proměnných z .env souboru (z kořenové složky projektu)
project_root = Path(__file__).resolve().parent.parent
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)

# API klíče
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
AI_MODEL = os.getenv("AI_MODEL", "gemini-2.5-flash")

# Cesty ke složkám
BACKEND_ROOT = Path(__file__).parent
UPLOAD_DIR = BACKEND_ROOT / "uploads"
OUTPUT_DIR = BACKEND_ROOT / "outputs"
LOGS_DIR = BACKEND_ROOT / "logs"

# Vytvoření složek pokud neexistují
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Konfigurace Flask
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
ALLOWED_EXTENSIONS = {'pdf'}

