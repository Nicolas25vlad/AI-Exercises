from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1)
    pergunta: str = Field(min_length=1)


class ChatResponse(BaseModel):
    resposta: str
    agentes_chamados: list[str] = []


class SessionResponse(BaseModel):
    session_id: str
    resumo: str = ""


class HistoryResponse(BaseModel):
    session_id: str
    mensagens: list[dict]
