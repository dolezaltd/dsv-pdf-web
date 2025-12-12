"""Konfigurace projektu."""
import os
from pathlib import Path
from dotenv import load_dotenv
from .api_keys import get_api_key

# Načtení proměnných z .env souboru
load_dotenv()

# API klíče - z .env souboru nebo environment proměnných
OPENAI_API_KEY = get_api_key("openai", fallback_env=True)
ANTHROPIC_API_KEY = get_api_key("anthropic", fallback_env=True)
GOOGLE_API_KEY = get_api_key("google", fallback_env=True)

# Cesty ke složkám - relativní k kořenové složce projektu
PROJECT_ROOT = Path(__file__).parent.parent  # Root projektu (o úroveň výš než src/)
INPUT_DIR = Path(os.getenv("PDF_INPUT_DIR", PROJECT_ROOT / "input"))
OUTPUT_DIR = Path(os.getenv("PDF_OUTPUT_DIR", PROJECT_ROOT / "output"))

# Vytvoření složek pokud neexistují
INPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# AI Model konfigurace
# Používá se pouze Google Gemini
# Podporované modely: gemini-2.5-flash, gemini-2.5-flash-lite, gemini-1.5-pro
AI_MODEL = os.getenv("AI_MODEL", "gemini-2.5-flash")  # Google Gemini 2.5 Flash (výchozí) - podporuje až 1M tokenů

