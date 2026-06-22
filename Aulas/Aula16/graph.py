# type: ignore
from langgraph.graph import StateGraph, MessagesState, END
from langgraph.checkpoint.memory import MemorySaver
import operator
from typing import Annotated

# ==============================================================================
# APPS GLOBAIS
# ==============================================================================
router_app = None
financeiro_app = None
agenda_app = None
faq_app = None
orquestrador_app = None

def set_apps(_router_app, _financeiro_app, _agenda_app, _faq_app, _orquestrador_app):
    global router_app, financeiro_app, agenda_app, faq_app, orquestrador_app
    router_app = _router_app
    financeiro_app = _financeiro_app
    agenda_app = _agenda_app
    faq_app = _faq_app
    orquestrador_app = _orquestrador_app

# ==============================================================================
# ESTADO
# ==============================================================================
class Estado(MessagesState):
    session_id:       str
    agentes_chamados: Annotated[list[str], operator.add]
    rota:             str
    saida_especialista: str

# ==============================================================================
# NÓS
# ==============================================================================

def no_roteador(estado: Estado) -> dict:
    saida = router_app.invoke(
        {"messages": estado["messages"]},
        config={"configurable": {"thread_id": estado["session_id"]}},
    )
    texto = saida["messages"][-1].content

    if "ROUTE=" not in texto:
        return {
            "agentes_chamados": ["roteador"],
            "rota": "fim",
            "messages": [{"role": "assistant", "content": texto}],
        }

    rota = "fim"
    for linha in texto.splitlines():
        if linha.startswith("ROUTE="):
            rota = linha.split("=", 1)[1].strip()
            break

    # Adiciona a mensagem do roteador como system/human para o próximo especialista
    return {
        "agentes_chamados": ["roteador"],
        "rota": rota,
        "messages": [{"role": "system", "content": texto}],  # protocolo para o especialista
    }


def no_financeiro(estado: Estado) -> dict:
    saida = financeiro_app.invoke(
        {"messages": estado["messages"]},
        config={"configurable": {"thread_id": estado["session_id"]}},
    )
    return {
        "saida_especialista": saida["messages"][-1].content,
        "agentes_chamados": ["financeiro"],
    }


def no_agenda(estado: Estado) -> dict:
    saida = agenda_app.invoke(
        {"messages": estado["messages"]},
        config={"configurable": {"thread_id": estado["session_id"]}},
    )
    return {
        "saida_especialista": saida["messages"][-1].content,
        "agentes_chamados": ["agenda"],
    }


def no_faq(estado: Estado) -> dict:
    saida = faq_app.invoke(
        {"messages": estado["messages"]},
        config={"configurable": {"thread_id": estado["session_id"]}},
    )
    return {
        "saida_especialista": saida["messages"][-1].content,
        "agentes_chamados": ["faq"],
        "messages": [{"role": "assistant", "content": saida["messages"][-1].content}],
    }


def no_orquestrador(estado: Estado) -> dict:
    saida = orquestrador_app.invoke(
        {"messages": [{"role": "human", "content": estado["saida_especialista"]}]},
        config={"configurable": {"thread_id": estado["session_id"]}},
    )
    return {
        "agentes_chamados": ["orquestrador"],
        "messages": [{"role": "assistant", "content": saida["messages"][-1].content}],
    }


def decidir_especialista(estado: Estado) -> str:
    rota = estado.get("rota", "fim")
    return rota if rota in ("financeiro", "agenda", "faq") else "fim"


# ==============================================================================
# CONSTRUÇÃO DO GRAFO
# ==============================================================================
grafo = StateGraph(Estado)

grafo.add_node("roteador", no_roteador)
grafo.add_node("financeiro", no_financeiro)
grafo.add_node("agenda", no_agenda)
grafo.add_node("faq", no_faq)
grafo.add_node("orquestrador", no_orquestrador)

grafo.set_entry_point("roteador")

grafo.add_conditional_edges(
    "roteador",
    decidir_especialista,
    {
        "financeiro": "financeiro",
        "agenda": "agenda",
        "faq": "faq",
        "fim": END,
    },
)

grafo.add_edge("financeiro", "orquestrador")
grafo.add_edge("agenda", "orquestrador")
grafo.add_edge("orquestrador", END)
grafo.add_edge("faq", END)

memory = MemorySaver()
FLUXO_AGENTES = grafo.compile(checkpointer=memory)