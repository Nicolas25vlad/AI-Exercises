from fastapi import APIRouter

from app.graph import executar_fluxo
from app.schemas import ChatRequest, ChatResponse

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def conversar(requisicao: ChatRequest) -> ChatResponse:
    """Uma mensagem do usuário, uma resposta do assessor."""
    resposta, agentes_chamados = executar_fluxo(
        requisicao.pergunta,
        requisicao.session_id,
        requisicao.user_id,
    )
    return ChatResponse(resposta=resposta, agentes_chamados=agentes_chamados)
