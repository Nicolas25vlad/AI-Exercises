from fastapi import APIRouter, HTTPException

from app.graph import executar_fluxo
from app.schemas import ChatRequest, ChatResponse

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    try:
        resposta, agentes = executar_fluxo(request.pergunta, request.session_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Falha ao processar a mensagem") from exc
    return ChatResponse(resposta=resposta, agentes_chamados=agentes)
