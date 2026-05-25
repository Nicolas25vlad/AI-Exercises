
import operator
from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, END

from langgraph.checkpoint.memory import MemorySaver


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
class Estado(TypedDict):
    input:              str                                  # sobrescrito a cada etapa
    session_id:         str                                  # ID da sessão
    agentes_chamados:   Annotated[list[str], operator.add]  # acumula entre nós
    saida_especialista: str                                  # JSON do especialista ativo
    resposta_final:     str                                  # resposta para o usuário


# ==============================================================================
# NÓS
# ==============================================================================
def no_roteador(estado: Estado) -> dict:
    saida = router_app.invoke(
        {"messages": [{"role": "human", "content": estado["input"]}]},
        config={"configurable": {"thread_id": estado["session_id"]}},
    )
    texto = saida["messages"][-1].text

    # Resposta direta (saudação, fora de escopo): já escreve no campo final
    if not texto.strip().startswith("ROUTE="):
        return {
            "agentes_chamados": ["roteador"],
            "resposta_final":   texto,
        }

    # Encaminhamento: sobrescreve input com o protocolo para o especialista
    return {
        "input":            texto,
        "agentes_chamados": ["roteador"],
    }


def no_financeiro(estado: Estado) -> dict:
    saida = financeiro_app.invoke(
        {"messages": [{"role": "human", "content": estado["input"]}]},
        config={"configurable": {"thread_id": {estado['session_id']}}},
    )
    return {
        "saida_especialista": saida["messages"][-1].text,
        "agentes_chamados":   ["financeiro"],
    }


def no_agenda(estado: Estado) -> dict:
    saida = agenda_app.invoke(
        {"messages": [{"role": "human", "content": estado["input"]}]},
        config={"configurable": {"thread_id": {estado['session_id']}}},
    )
    return {
        "saida_especialista": saida["messages"][-1].text,
        "agentes_chamados":   ["agenda"],
    }


def no_faq(estado: Estado) -> dict:
    saida = faq_app.invoke(
        {"messages": [{"role": "human", "content": estado["input"]}]},
        config={"configurable": {"thread_id": {estado['session_id']}}},
    )
    return {
        "saida_especialista": saida["messages"][-1].text,
        "resposta_final":     saida["messages"][-1].text,  # bypassa o orquestrador
        "agentes_chamados":   ["faq"],
    }


def no_orquestrador(estado: Estado) -> dict:
    saida = orquestrador_app.invoke(
        {"messages": [{"role": "human", "content": estado["saida_especialista"]}]},
        config={"configurable": {"thread_id": {estado['session_id']}}},
    )
    return {
        "resposta_final":   saida["messages"][-1].text,
        "agentes_chamados": ["orquestrador"],
    }


# ==============================================================================
# FUNÇÃO DE DECISÃO
# ==============================================================================
def decidir_especialista(estado: Estado) -> str:
    """Lê o protocolo do roteador e devolve o nome do próximo nó."""
    texto = estado["input"].strip()

    if not texto.startswith("ROUTE="):
        return "fim"   # resposta direta já foi escrita no nó do roteador

    rota = texto.split("\n", 1)[0].split("=", 1)[1].strip()
    return rota if rota in ("financeiro", "agenda", "faq") else "fim"


# ==============================================================================
# CONSTRUÇÃO DO GRAFO
# ==============================================================================
grafo = StateGraph(Estado)

grafo.add_node("roteador",     no_roteador)
grafo.add_node("financeiro",   no_financeiro)
grafo.add_node("agenda",       no_agenda)
grafo.add_node("faq",          no_faq)
grafo.add_node("orquestrador", no_orquestrador)

grafo.set_entry_point("roteador")

grafo.add_conditional_edges(
    "roteador",
    decidir_especialista,
    {
        "financeiro": "financeiro",
        "agenda":     "agenda",
        "faq":        "faq",
        "fim":        END,       # resposta direta: sem especialista nem orquestrador
    },
)

grafo.add_edge("financeiro",   "orquestrador")
grafo.add_edge("agenda",       "orquestrador")
grafo.add_edge("orquestrador", END)
grafo.add_edge("faq",          END)   # FAQ bypassa o orquestrador

# Memória centralizada no grafo — persiste o Estado inteiro entre turns
memory = MemorySaver()


#armazenando os apps no grafo para serem usados nos nós







FLUXO_AGENTES = grafo.compile(checkpointer=memory)

