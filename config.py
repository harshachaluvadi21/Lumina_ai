import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base directories
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
CHROMA_DIR = BASE_DIR / "chroma_db"
APP_DATA_DIR = BASE_DIR / "app_data"

# Create directories if they do not exist
for directory in [UPLOAD_DIR, CHROMA_DIR, APP_DATA_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Databases
MONGODB_URI = os.getenv("MONGODB_URI", "")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "ai_summarizer")
CHROMA_DB_DIR = str(CHROMA_DIR)

# SQLite fallback path
SQLITE_DB_PATH = str(APP_DATA_DIR / "local_storage.db")

# System settings
PORT = int(os.getenv("STREAMLIT_SERVER_PORT", "8501"))

def is_gemini_available() -> bool:
    return bool(GEMINI_API_KEY)

def is_groq_available() -> bool:
    return bool(GROQ_API_KEY)

def is_mongodb_configured() -> bool:
    return bool(MONGODB_URI)
