from datetime import datetime, timezone
from uuid import uuid4

from pymongo import MongoClient

from app.config import MONGODB_URI
from app.llms import llm_rapido

_mongo = None
_collection = None
_sessoes_ativas: dict[str, str] = {}


def _get_collection():
    global _mongo, _collection
    if _collection is None:
        _mongo = MongoClient(MONGODB_URI)
        _collection = _mongo["assessor"]["sessoes"]
        _collection.create_index("session_id")
        _collection.create_index("iniciada_em")
    return _collection

_PROMPT_RESUMO = """Você é um assistente que resume conversas de assessoria financeira e agenda.
Gere um resumo conciso em 2-4 frases capturando o que o usuário fez, perguntou e as
informações relevantes mencionadas. Responda apenas com o resumo.

Conversa:
{conversa}"""


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _sessao_ativa(session_id: str):
    return _get_collection().find_one(
        {"session_id": session_id, "encerrada_em": {"$exists": False}},
        sort=[("iniciada_em", -1)],
    )


def _doc_id_da_sessao(session_id: str) -> str | None:
    """
    Descobre o documento da sessão EM ANDAMENTO deste usuário, ou None.

    Olha primeiro o cache em memória (_sessoes_ativas). Se não achar, procura
    no MongoDB a sessão mais recente que ainda não foi encerrada — isto é, com
    resumo vazio.

    Essa segunda tentativa existe porque _sessoes_ativas vive na RAM do
    processo: um --reload do uvicorn no meio da conversa esvazia o dicionário.
    Sem ela, iniciar_sessao() criaria um documento novo para a mesma conversa a
    cada reinício, e encerrar_sessao() não acharia nada para resumir — sem erro
    nenhum, apenas silêncio.
    """
    doc_id = _sessoes_ativas.get(session_id)
    if doc_id:
        return doc_id

    doc = _get_collection().find_one(
        {"session_id": session_id, "resumo": {"$in": ["", None]}},
        {"_id": 1},
        sort=[("iniciada_em", -1)],
    )
    if not doc:
        return None

    _sessoes_ativas[session_id] = doc["_id"]
    return doc["_id"]


def iniciar_sessao(session_id: str) -> None:
    """
    Garante que existe um documento de sessão aberto para este session_id.
    Se já houver um (em memória ou no Mongo), não faz nada.
    """
    if _doc_id_da_sessao(session_id):
        return

    agora = _agora()
    doc_id = str(uuid4())
    _get_collection().insert_one(
        {
            "_id": doc_id,
            "session_id": session_id,
            "iniciada_em": agora,
            "atualizada_em": agora,
            "mensagens": [],
        }
    )
    _sessoes_ativas[session_id] = doc_id


def salvar_mensagem(session_id: str, role: str, content: str) -> None:
    """Adiciona uma mensagem ao array de mensagens da sessão ativa."""
    iniciar_sessao(session_id)
    doc_id = _doc_id_da_sessao(session_id)
    _get_collection().update_one(
        {"_id": doc_id},
        {
            "$push": {"mensagens": {"role": role, "content": content}},
            "$set": {"atualizada_em": _agora()},
        },
    )


def recuperar_historico(
    session_id: str, busca: str = "", limite: int = 3
) -> list[dict]:
    """Recupera resumos de sessões anteriores já encerradas."""

    # só sessões DESTE usuário que já têm resumo (= já encerradas).
    # O $nin descarta a sessão em andamento, cujo resumo ainda está vazio —
    # sem ele a tool devolveria a própria conversa atual como se fosse passado.
    filtro: dict = {"session_id": session_id, "resumo": {"$nin": ["", None]}}

    # se houver termo de busca, filtra resumos que o contenham (case-insensitive).
    # Acrescenta ao filtro existente em vez de substituí-lo, senão o $nin acima
    # se perderia e a sessão atual voltaria para o resultado.
    if busca:
        filtro["resumo"]["$regex"] = busca
        filtro["resumo"]["$options"] = "i"

    docs = (
        _get_collection()
        .find(filtro, {"resumo": 1, "iniciada_em": 1})
        .sort("iniciada_em", -1)
        .limit(limite)
    )
    return [
        {"doc_id": doc["_id"], "iniciada_em": doc["iniciada_em"], "resumo": doc["resumo"]}
        for doc in docs
    ]


def recuperar_mensagens(doc_id: str) -> list[dict]:
    """Busca as mensagens completas de um documento específico."""
    doc = _get_collection().find_one({"_id": doc_id}, {"mensagens": 1})
    if doc:
        return doc.get("mensagens", [])

    # Compatibilidade com a rota legada, que recebe session_id.
    sessao = _sessao_ativa(doc_id) or _get_collection().find_one(
        {"session_id": doc_id}, sort=[("iniciada_em", -1)]
    )
    return sessao.get("mensagens", []) if sessao else []


def encerrar_sessao(session_id: str) -> str:
    doc_id = _doc_id_da_sessao(session_id)
    if not doc_id:
        return ""

    sessao = _get_collection().find_one({"_id": doc_id})
    if not sessao or not sessao.get("mensagens"):
        return ""
    conversa = "\n".join(
        f"{mensagem['role']}: {mensagem['content']}"
        for mensagem in sessao["mensagens"]
    )
    resumo = llm_rapido.invoke(_PROMPT_RESUMO.format(conversa=conversa)).content.strip()
    _get_collection().update_one(
        {"_id": doc_id},
        {"$set": {"resumo": resumo, "encerrada_em": _agora(), "atualizada_em": _agora()}},
    )
    _sessoes_ativas.pop(session_id, None)
    return resumo
