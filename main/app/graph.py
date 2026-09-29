import json
import operator
import re
from typing import Annotated

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, MessagesState, StateGraph

from app.agents import agenda_app, faq_app, financeiro_app, orquestrador_app, router_app
from app.guardrail import anonimizar_entrada, guardrail_entrada, guardrail_saida
from app.memory import salvar_mensagem
from app.perfil import consultar_perfil

    
class Estado(MessagesState):
    session_id: str
    user_id: str
    agentes_chamados: Annotated[list[str], operator.add]
    rota: str
    mapa_pii: dict[str, str]
    bloqueado: bool
    saida_especialista: str
    resposta_final: str


def _texto(mensagem) -> str:
    return mensagem.content if hasattr(mensagem, "content") else mensagem.get("content", "")


def _pergunta_sobre_perfil(pergunta: str) -> bool:
    return bool(re.search(
        r"renda|sal[aá]rio|gasto\s+(fixo\s+)?mensal|horizonte|perfil\s+investidor|restri",
        pergunta.lower(),
    ))


def _resposta_perfil(perfil: dict, pergunta: str) -> str:
    if perfil["status"] != "ok":
        return json.dumps({
            "dominio": "financeiro",
            "intencao": "consultar",
            "resposta": perfil["mensagem"],
            "recomendacao": "Acesse a tela Perfil para cadastrar seus dados.",
        }, ensure_ascii=False)

    dados = perfil["perfil"]
    texto = pergunta.lower()
    partes = []
    if "renda" in texto or "salário" in texto or "salario" in texto:
        partes.append(f"Sua renda mensal é de R$ {dados['renda_mensal']:.2f}.")
    if "gasto" in texto:
        partes.append(f"Seu gasto fixo mensal é de R$ {dados['gasto_fixo_mensal']:.2f}.")
    if "horizonte" in texto or "tempo" in texto:
        partes.append(f"Seu horizonte é de {dados['horizonte_meses']} meses.")
    if "perfil" in texto or "investidor" in texto:
        partes.append(f"Seu perfil investidor é {dados['perfil_investidor']}.")
    if "restri" in texto:
        restricoes = perfil["restricoes_relevantes"] or dados["restricoes"]
        partes.append("Suas restrições são: " + "; ".join(restricoes) + ".")
    if not partes:
        partes.append(f"Seu perfil está cadastrado com horizonte de {dados['horizonte_meses']} meses.")
    return json.dumps({
        "dominio": "financeiro",
        "intencao": "consultar",
        "resposta": " ".join(partes),
        "recomendacao": "",
    }, ensure_ascii=False)


def no_guardrail_entrada(estado: Estado) -> dict:
    verificacao = guardrail_entrada(_texto(estado["messages"][-1]))
    if verificacao["bloqueado"]:
        return {
            "bloqueado": True,
            "resposta_final": f"[BLOQUEADO] {verificacao['mensagem']}",
            "agentes_chamados": ["guardrail_entrada"],
        }
    return {"bloqueado": False, "agentes_chamados": ["guardrail_entrada"]}


def decidir_pos_guardrail_entrada(estado: Estado) -> str:
    return "saida" if estado.get("bloqueado") else "roteador"


def no_roteador(estado: Estado) -> dict:
    saida = router_app.invoke(
        {"messages": estado["messages"]},
        config={
            "configurable": {
                "thread_id": estado["session_id"],
                "user_id": estado["user_id"],
            }
        },
    )
    texto = _texto(saida["messages"][-1])
    rota = "fim"
    for linha in texto.splitlines():
        if linha.startswith("ROUTE="):
            rota = linha.split("=", 1)[1].strip()
            break
    return {
        "agentes_chamados": ["roteador"],
        "rota": rota,
        "messages": [{"role": "system", "content": texto}],
    }


def no_financeiro(estado: Estado) -> dict:
    mensagens = estado["messages"]
    pergunta = _texto(mensagens[-1])
    if _pergunta_sobre_perfil(pergunta):
        perfil = consultar_perfil(estado["user_id"], pergunta)
        return {
            "saida_especialista": _resposta_perfil(perfil, pergunta),
            "agentes_chamados": ["financeiro"],
        }
    saida = financeiro_app.invoke(
        {"messages": mensagens},
        config={
            "configurable": {
                "thread_id": estado["session_id"],
                "user_id": estado["user_id"],
            }
        },
    )
    return {
        "saida_especialista": _texto(saida["messages"][-1]),
        "agentes_chamados": ["financeiro"],
    }


def no_agenda(estado: Estado) -> dict:
    saida = agenda_app.invoke(
        {"messages": estado["messages"]},
        config={
            "configurable": {
                "thread_id": estado["session_id"],
                "user_id": estado["user_id"],
            }
        },
    )
    return {
        "saida_especialista": _texto(saida["messages"][-1]),
        "agentes_chamados": ["agenda"],
    }


def no_faq(estado: Estado) -> dict:
    saida = faq_app.invoke(
        {"messages": estado["messages"]},
        config={
            "configurable": {
                "thread_id": estado["session_id"],
                "user_id": estado["user_id"],
            }
        },
    )
    texto = _texto(saida["messages"][-1])
    return {
        "saida_especialista": texto,
        "agentes_chamados": ["faq"],
        "messages": [{"role": "assistant", "content": texto}],
    }


def no_orquestrador(estado: Estado) -> dict:
    saida = orquestrador_app.invoke(
        {"messages": [{"role": "human", "content": estado["saida_especialista"]}]},
        config={
            "configurable": {
                "thread_id": estado["session_id"],
                "user_id": estado["user_id"],
            }
        },
    )
    return {
        "agentes_chamados": ["orquestrador"],
        "messages": [{"role": "assistant", "content": _texto(saida["messages"][-1])}],
    }


def decidir_especialista(estado: Estado) -> str:
    rota = estado.get("rota", "fim")
    return rota if rota in {"financeiro", "agenda", "faq"} else "saida"


def no_guardrail_saida(estado: Estado) -> dict:
    if estado.get("bloqueado"):
        return {"agentes_chamados": ["guardrail_saida"]}
    resposta = _texto(estado["messages"][-1])
    revisada = guardrail_saida(resposta, estado.get("mapa_pii", {}), restaurar_pii=False)
    return {
        "resposta_final": revisada["conteudo"],
        "agentes_chamados": ["guardrail_saida"],
    }


grafo = StateGraph(Estado)
grafo.add_node("guardrail_entrada", no_guardrail_entrada)
grafo.add_node("roteador", no_roteador)
grafo.add_node("financeiro", no_financeiro)
grafo.add_node("agenda", no_agenda)
grafo.add_node("faq", no_faq)
grafo.add_node("orquestrador", no_orquestrador)
grafo.add_node("guardrail_saida", no_guardrail_saida)
grafo.set_entry_point("guardrail_entrada")
grafo.add_conditional_edges(
    "guardrail_entrada",
    decidir_pos_guardrail_entrada,
    {"roteador": "roteador", "saida": "guardrail_saida"},
)
grafo.add_conditional_edges(
    "roteador",
    decidir_especialista,
    {
        "financeiro": "financeiro",
        "agenda": "agenda",
        "faq": "faq",
        "saida": "guardrail_saida",
    },
)
grafo.add_edge("financeiro", "orquestrador")
grafo.add_edge("agenda", "orquestrador")
grafo.add_edge("orquestrador", "guardrail_saida")
grafo.add_edge("faq", "guardrail_saida")
grafo.add_edge("guardrail_saida", END)

fluxo_agentes = grafo.compile(checkpointer=MemorySaver())


def executar_fluxo(
    pergunta: str, session_id: str, user_id: str = "usuario_teste"
) -> tuple[str, list[str]]:
    salvar_mensagem(session_id, "usuario", pergunta, user_id=user_id)
    mensagem, mapa_pii = anonimizar_entrada(pergunta)
    estado = fluxo_agentes.invoke(
        {
            "messages": [{"role": "human", "content": mensagem}],
            "session_id": session_id,
            "user_id": user_id,
            "agentes_chamados": [],
            "rota": "",
            "mapa_pii": mapa_pii,
            "bloqueado": False,
            "saida_especialista": "",
            "resposta_final": "",
        },
        config={
            "configurable": {"thread_id": session_id, "user_id": user_id}
        },
    )
    resposta = estado.get("resposta_final") or "Não foi possível obter uma resposta."
    salvar_mensagem(session_id, "assistente", resposta, user_id=user_id)
    agentes = list(dict.fromkeys(estado.get("agentes_chamados", [])))
    return resposta, agentes
