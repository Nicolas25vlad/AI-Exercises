from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str = Field(..., examples=["id_usuario"])
    pergunta: str = Field(..., min_length=1, examples=["gastei 50 reais no mercado"])


class ChatResponse(BaseModel):
    resposta: str
    agentes_chamados: list[str] = Field(default_factory=list)


class SessionResponse(BaseModel):
    session_id: str
    resumo: str | None = None


class HistoryResponse(BaseModel):
    session_id: str
    mensagens: list[dict]
