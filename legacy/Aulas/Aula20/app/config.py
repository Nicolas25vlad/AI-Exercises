import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
DATABASE_URL = os.getenv("DATABASE_URL", "")
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
FAQ_PDF_PATH = BASE_DIR / "data" / "faq.pdf"
