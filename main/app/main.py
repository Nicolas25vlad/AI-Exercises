from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from app.config import FRONTEND_DIR, validar_config
from app.routes import chat, perfil, sessions

for _problema in validar_config():
    print(f"[config] ATENÇÃO: {_problema}")

app = FastAPI(title="Assessor.AI", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_credentials=True,
    allow_headers=["*"],
)
app.include_router(chat.router)
app.include_router(sessions.router)
app.include_router(perfil.router)


@app.get("/", include_in_schema=False)
def abrir_perfil() -> RedirectResponse:
    return RedirectResponse("/perfil.html")


@app.get("/health")
def health() -> dict[str, object]:
    problemas = validar_config()
    return {
        "status": "ok" if not problemas else "atencao",
        "problemas_de_configuracao": problemas,
    }


app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
