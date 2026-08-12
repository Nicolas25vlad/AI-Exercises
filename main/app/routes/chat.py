from fastapi import APIRouter

from app.schemas import ChatRequest, ChatResponse

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def conversar(requisicao: ChatRequest) -> ChatResponse:
    return ChatResponse(
        resposta=(
            f"Recebi sua mensagem na sessão '{requisicao.session_id}': "
            f'"{requisicao.pergunta}". O grafo ainda não está ligado nesta rota.'
        ),
        agentes_chamados=["eco_de_teste"],
    )
