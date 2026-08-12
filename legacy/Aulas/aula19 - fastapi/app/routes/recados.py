from fastapi import APIRouter
from app.models import Recado
import app.storage

router = APIRouter()

@router.post("/recados")
def criar_recado(recado: Recado):
    return {"recebido": recado}
#salvar o recado na sessão

@router.post("/recados/salvar/{sessao_id}")
def salvar_recado(sessao_id: str, recado: Recado):
    app.storage.salvar(sessao_id, recado.autor, recado.mensagem)
    return {"mensagem": "Recado salvo com sucesso"}

@router.get("/recados/listar/{sessao_id}")
def listar_recados(sessao_id: str):
    recados = app.storage.listar(sessao_id)
    return {"recados": recados}
