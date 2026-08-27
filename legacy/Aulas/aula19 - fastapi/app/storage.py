from fastapi import HTTPException, status


recados_por_sessao: dict[str, list[dict]] = {}

def salvar(sessao_id, autor, mensagem):
    recados_por_sessao.setdefault(sessao_id, []).append(
        {"autor": autor, "mensagem": mensagem}
    )

def listar(sessao_id: str) -> list[dict]:
    if sessao_id not in recados_por_sessao:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sessão não encontrada",
        )

    return recados_por_sessao[sessao_id]