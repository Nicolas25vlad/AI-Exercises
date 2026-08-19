from fastapi import FastAPI

from app.models import Recado
from app.routes.recados import router as recados_router

app = FastAPI()

@app.get("/")
def raiz():
    return {"mensagem": "API de recados no ar"}


app.include_router(recados_router, prefix="/v1")


