from datetime import datetime, timezone
from uuid import uuid4

from pymongo import MongoClient

from app.config import MONGODB_URI
from app.llms import llm_rapido

_mongo = MongoClient(MONGODB_URI)
_collection = _mongo["assessor"]["sessoes"]
_collection.create_index("session_id")
_collection.create_index("iniciada_em")

_PROMPT_RESUMO = """Você é um assistente que resume conversas de assessoria financeira e agenda.
Gere um resumo conciso em 2-4 frases capturando o que o usuário fez, perguntou e as
informações relevantes mencionadas. Responda apenas com o resumo.

Conversa:
{conversa}"""


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _sessao_ativa(session_id: str):
    return _collection.find_one(
        {"session_id": session_id, "encerrada_em": {"$exists": False}},
        sort=[("iniciada_em", -1)],
    )


def iniciar_sessao(session_id: str) -> None:
    agora = _agora()
    _collection.insert_one(
        {
            "_id": str(uuid4()),
            "session_id": session_id,
            "iniciada_em": agora,
            "atualizada_em": agora,
            "mensagens": [],
        }
    )


def salvar_mensagem(session_id: str, role: str, content: str) -> None:
    sessao = _sessao_ativa(session_id)
    if not sessao:
        raise KeyError(f"Sessão não encontrada: {session_id}")
    _collection.update_one(
        {"_id": sessao["_id"]},
        {
            "$push": {"mensagens": {"role": role, "content": content}},
            "$set": {"atualizada_em": _agora()},
        },
    )


def recuperar_mensagens(session_id: str) -> list[dict]:
    sessao = _sessao_ativa(session_id) or _collection.find_one(
        {"session_id": session_id}, sort=[("iniciada_em", -1)]
    )
    return sessao.get("mensagens", []) if sessao else []


def recuperar_historico(session_id: str) -> str:
    return "\n".join(
        f"{mensagem['role']}: {mensagem['content']}"
        for mensagem in recuperar_mensagens(session_id)
    )


def encerrar_sessao(session_id: str) -> str:
    sessao = _sessao_ativa(session_id)
    if not sessao or not sessao.get("mensagens"):
        return ""
    conversa = "\n".join(
        f"{mensagem['role']}: {mensagem['content']}"
        for mensagem in sessao["mensagens"]
    )
    resumo = llm_rapido.invoke(_PROMPT_RESUMO.format(conversa=conversa)).content.strip()
    _collection.update_one(
        {"_id": sessao["_id"]},
        {"$set": {"resumo": resumo, "encerrada_em": _agora(), "atualizada_em": _agora()}},
    )
    return resumo
