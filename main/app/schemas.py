from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """O que o navegador envia no POST /chat."""

    session_id: str = Field(
        ...,
        description="Identifica a conversa (UUID gerado pelo front a cada sessão).",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    user_id: str = Field(
        default="usuario_teste",
        description="Identifica o usuário de forma estável entre sessões. "
                    "É o que permite a memória de longo prazo funcionar.",
        examples=["usuario_teste"],
    )
    pergunta: str = Field(
        ...,
        min_length=1,
        description="A mensagem do usuário — o que antes vinha do input().",
        examples=["gastei 50 reais no mercado hoje"],
    )


class ChatResponse(BaseModel):
    resposta: str
    agentes_chamados: list[str] = Field(default_factory=list)


class SessionResponse(BaseModel):
    session_id: str
    resumo: str | None = None


class HistoryResponse(BaseModel):
    session_id: str
    mensagens: list[dict]
