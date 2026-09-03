import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
FRONTEND_DIR = BASE_DIR / "frontend"
load_dotenv(BASE_DIR / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
QDRANT_URL = os.getenv("QDRANT_CLUSTER_ENDPOINT")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
FAQ_PDF_PATH = DATA_DIR / "faq.pdf"

OBRIGATORIAS = {
    "GEMINI_API_KEY": GEMINI_API_KEY,
    "GROQ_API_KEY": GROQ_API_KEY,
    "DATABASE_URL": DATABASE_URL,
    "MONGODB_URI": MONGODB_URI,
    "QDRANT_URL": QDRANT_URL,
    "QDRANT_API_KEY": QDRANT_API_KEY,
}


def validar_config() -> list[str]:
    problemas = [
        f"Variável ausente no .env: {nome}"
        for nome, valor in OBRIGATORIAS.items()
        if not valor
    ]
    if not FAQ_PDF_PATH.exists():
        problemas.append(f"PDF do FAQ não encontrado em: {FAQ_PDF_PATH}")
    return problemas
