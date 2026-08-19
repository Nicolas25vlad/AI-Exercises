from uuid import uuid4

from fastapi import APIRouter

from app.memory import encerrar_sessao, iniciar_sessao, recuperar_mensagens
from app.schemas import HistoryResponse, SessionResponse

router = APIRouter(prefix="/sessions")


@router.post("", response_model=SessionResponse)
def create_session() -> SessionResponse:
    session_id = str(uuid4())
    iniciar_sessao(session_id)
    return SessionResponse(session_id=session_id)


@router.delete("/{session_id}", response_model=SessionResponse)
def close_session(session_id: str) -> SessionResponse:
    return SessionResponse(session_id=session_id, resumo=encerrar_sessao(session_id))


@router.get("/{session_id}/historico", response_model=HistoryResponse)
def history(session_id: str) -> HistoryResponse:
    return HistoryResponse(session_id=session_id, mensagens=recuperar_mensagens(session_id))
