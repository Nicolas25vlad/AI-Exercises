import sys
import os
from pathlib import Path
from typing import Annotated, Literal, Optional

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations
from pydantic import Field

from app.config import DATABASE_URL
from app.tools.financeiro import (
    add_transaction as _add_transaction,
    daily_balance as _daily_balance,
    query_transactions as _query_transactions,
    total_balance as _total_balance,
    update_transaction as _update_transaction,
)
from app.tools.agenda import add_event as _add_event, query_events as _query_events

mcp = MCPServer(
    "assessor-financeiro",
    version="1.0.0",
    instructions="Ferramentas financeiras e de agenda do Assessor. Valores monetários são em reais.",
)

READ_ONLY = ToolAnnotations(read_only_hint=True)
WRITES = ToolAnnotations(read_only_hint=False, destructive_hint=False)
AGENDA_USER_ID = os.getenv("AGENDA_USER_ID", "usuario_teste")


@mcp.tool(
    title="Saldo total",
    description="Retorna receitas, despesas e saldo de todo o histórico financeiro.",
    annotations=READ_ONLY,
)
def total_balance() -> dict:
    return _total_balance.invoke({"source_text": "Consulta via MCP"})


@mcp.tool(
    title="Consultar transações",
    description="Lista até 20 transações por tipo, opcionalmente a partir de uma data.",
    annotations=READ_ONLY,
)
def query_transactions(
    tipo: Annotated[Literal["INCOME", "EXPENSES", "TRANSFER"], Field(description="Tipo da transação.")],
    occurred_at: Annotated[Optional[str], Field(description="Data ISO 8601 ou mês YYYY-MM.")] = None,
) -> dict:
    return _query_transactions.invoke(
        {"source_text": "Consulta via MCP", "tipo": tipo, "occurred_at": occurred_at}
    )


@mcp.tool(
    title="Saldo diário",
    description="Retorna receitas, despesas e saldo de um dia, mês ou ano.",
    annotations=READ_ONLY,
)
def daily_balance(
    occurred_at: Annotated[Optional[str], Field(description="Data ISO 8601 ou mês YYYY-MM.")] = None,
    periodo: Annotated[Literal["dia", "mes", "ano"], Field(description="Período a consultar.")] = "dia",
) -> dict:
    return _daily_balance.invoke(
        {"source_text": "Consulta via MCP", "occurred_at": occurred_at, "periodo": periodo}
    )


@mcp.tool(
    title="Registrar transação",
    description="Registra uma transação financeira. Confirme os dados antes de executar.",
    annotations=WRITES,
)
def add_transaction(
    amount: Annotated[float, Field(gt=0, description="Valor positivo em reais.")],
    source_text: Annotated[str, Field(description="Texto original do lançamento.")],
    type_name: Annotated[Literal["INCOME", "EXPENSES", "TRANSFER"], Field(description="Tipo da transação.")],
    category_name: Annotated[Optional[str], Field(description="Categoria em português.")] = None,
    occurred_at: Annotated[Optional[str], Field(description="Data ISO 8601.")] = None,
    description: Annotated[Optional[str], Field(description="Descrição.")] = None,
    payment_method: Annotated[Optional[str], Field(description="Forma de pagamento.")] = None,
) -> dict:
    return _add_transaction.invoke(
        {
            "amount": amount,
            "source_text": source_text,
            "type_name": type_name,
            "category_name": category_name,
            "occurred_at": occurred_at,
            "description": description,
            "payment_method": payment_method,
        }
    )


@mcp.tool(
    title="Atualizar transação",
    description="Atualiza uma transação pelo ID ou por texto e data local. Confirme antes de executar.",
    annotations=WRITES,
)
def update_transaction(
    id: Annotated[Optional[int], Field(description="ID da transação.")] = None,
    match_text: Annotated[Optional[str], Field(description="Texto para localizar a transação.")] = None,
    date_local: Annotated[Optional[str], Field(description="Data local YYYY-MM-DD.")] = None,
    amount: Annotated[Optional[float], Field(gt=0, description="Novo valor positivo em reais.")] = None,
    type_name: Annotated[Optional[Literal["INCOME", "EXPENSES", "TRANSFER"]], Field(description="Novo tipo.")] = None,
    category_name: Annotated[Optional[str], Field(description="Nova categoria.")] = None,
    description: Annotated[Optional[str], Field(description="Nova descrição.")] = None,
    payment_method: Annotated[Optional[str], Field(description="Nova forma de pagamento.")] = None,
    occurred_at: Annotated[Optional[str], Field(description="Novo timestamp ISO 8601.")] = None,
) -> dict:
    return _update_transaction.invoke(
        {
            "id": id,
            "match_text": match_text,
            "date_local": date_local,
            "amount": amount,
            "type_name": type_name,
            "category_name": category_name,
            "description": description,
            "payment_method": payment_method,
            "occurred_at": occurred_at,
        }
    )


@mcp.tool(
    title="Consultar agenda",
    description="Lista compromissos por data local YYYY-MM-DD e/ou trecho do título.",
    annotations=READ_ONLY,
)
def query_events(
    date_local: Annotated[Optional[str], Field(description="Data local YYYY-MM-DD.")] = None,
    text: Annotated[Optional[str], Field(description="Trecho do título.")] = None,
    limit: Annotated[int, Field(ge=1, le=200, description="Máximo de resultados.")] = 50,
) -> dict | list:
    return _query_events.invoke(
        {"date_local": date_local, "text": text, "limit": limit},
        config={"configurable": {"user_id": AGENDA_USER_ID}},
    )


@mcp.tool(
    title="Registrar compromisso",
    description="Salva compromisso no banco local. Datas ISO 8601 com fuso.",
    annotations=WRITES,
)
def add_event(
    title: Annotated[str, Field(min_length=1, description="Título do compromisso.")],
    start_time: Annotated[str, Field(description="Início ISO 8601 com fuso.")],
    end_time: Annotated[str, Field(description="Fim ISO 8601 com fuso.")],
    source_text: Annotated[str, Field(min_length=1, description="Pedido original.")],
    location: Annotated[Optional[str], Field(description="Local.")] = None,
    notes: Annotated[Optional[str], Field(description="Observações.")] = None,
) -> dict:
    return _add_event.invoke(
        {"title": title, "start_time": start_time, "end_time": end_time,
         "source_text": source_text, "location": location, "notes": notes},
        config={"configurable": {"user_id": AGENDA_USER_ID}},
    )


if __name__ == "__main__":
    if not DATABASE_URL:
        print("[assessor-financeiro] DATABASE_URL ausente no .env", file=sys.stderr)
    mcp.run(transport="stdio")
