from datetime import datetime

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from app.tools.db import get_conn


def _user_id(config: RunnableConfig) -> str | None:
    return (config or {}).get("configurable", {}).get("user_id")


@tool
def add_event(
    title: str,
    start_time: str,
    end_time: str,
    source_text: str,
    config: RunnableConfig,
    location: str | None = None,
    notes: str | None = None,
) -> dict:
    """Registra um compromisso no banco local. Datas devem ser ISO 8601 com fuso."""
    user_id = _user_id(config)
    if not user_id:
        return {"status": "erro", "mensagem": "Usuário não identificado."}
    try:
        inicio = datetime.fromisoformat(start_time)
        fim = datetime.fromisoformat(end_time)
        if inicio.utcoffset() is None or fim.utcoffset() is None or fim <= inicio:
            raise ValueError
    except (TypeError, ValueError):
        return {"status": "erro", "mensagem": "Informe início e fim ISO 8601 válidos, com fuso, e fim posterior ao início."}

    conn = get_conn()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """INSERT INTO events (user_id, title, start_time, end_time, location, notes, source_text)
                   VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id""",
                (user_id, title, inicio, fim, location, notes, source_text),
            )
            event_id = cur.fetchone()[0]
    finally:
        conn.close()
    return {"status": "ok", "id": event_id}


@tool
def query_events(
    config: RunnableConfig,
    date_local: str | None = None,
    text: str | None = None,
    limit: int = 50,
) -> list[dict] | dict:
    """Consulta eventos por data local (America/Sao_Paulo) ou trecho do título."""
    user_id = _user_id(config)
    if not user_id:
        return {"status": "erro", "mensagem": "Usuário não identificado."}
    if not 1 <= limit <= 200:
        return {"status": "erro", "mensagem": "O limite deve ficar entre 1 e 200."}
    if date_local:
        try:
            datetime.strptime(date_local, "%Y-%m-%d")
        except ValueError:
            return {"status": "erro", "mensagem": "date_local deve estar no formato YYYY-MM-DD."}

    filtros = ["user_id = %s"]
    valores: list = [user_id]
    if date_local:
        filtros.append("end_time > (%s::date::timestamp AT TIME ZONE 'America/Sao_Paulo')")
        filtros.append("start_time < ((%s::date + 1)::timestamp AT TIME ZONE 'America/Sao_Paulo')")
        valores.extend((date_local, date_local))
    if text:
        filtros.append("title ILIKE %s")
        valores.append(f"%{text}%")
    valores.append(limit)
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""SELECT id, title, start_time, end_time, location, notes
                    FROM events WHERE {' AND '.join(filtros)}
                    ORDER BY start_time LIMIT %s""",
                valores,
            )
            rows = cur.fetchall()
    finally:
        conn.close()
    return [
        {"id": r[0], "titulo": r[1], "inicio": r[2].isoformat(), "fim": r[3].isoformat(), "local": r[4], "notas": r[5]}
        for r in rows
    ]


TOOLS_AGENDA = [add_event, query_events]
