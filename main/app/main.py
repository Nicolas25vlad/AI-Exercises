from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import FRONTEND_DIR, validar_config
from app.routes import chat, sessions

for _problema in validar_config():
    print(f"[config] ATENÇÃO: {_problema}")

app = FastAPI(title="Assessor.AI", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(chat.router)
app.include_router(sessions.router)


@app.get("/health")
def health() -> dict[str, object]:
    problemas = validar_config()
    return {
        "status": "ok" if not problemas else "atencao",
        "problemas_de_configuracao": problemas,
    }


app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
