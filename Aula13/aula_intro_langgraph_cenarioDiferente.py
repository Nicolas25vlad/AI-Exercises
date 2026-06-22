"""
Introdução ao LangGraph — Respondedor de Mensagens
===================================================
Cenário: o usuário envia uma mensagem. O grafo classifica
o sentimento e escolhe um tipo de resposta diferente.

Conceitos demonstrados (nesta ordem):
  1. Estado (TypedDict) — o dado que viaja entre nós
  2. Reducer (Annotated) — campo que acumula
  3. Nós — funções que lêem e retornam
  4. Aresta condicional — o if/else dentro do grafo
  5. compile() / invoke()
"""

import operator
from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, START, END
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os

load_dotenv()

llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

# ─────────────────────────────────────────────
# 1. ESTADO
# Campos que existem no grafo. Cada nó pode ler
# e retornar apenas o que ele alterar.
# ─────────────────────────────────────────────
class Estado(TypedDict):
    mensagem:   str                               # entrada do usuário
    sentimento: str                               # preenchido por no_classificar
    resposta:   str                               # preenchido por no_responder_*
    passos:     Annotated[list[str], operator.add]# acumula — não sobrescreve


# ─────────────────────────────────────────────
# 2. NÓS
# ─────────────────────────────────────────────
def no_classificar(estado: Estado) -> dict:
    r = llm.invoke([
        {"role": "system",  "content": "Responda APENAS com uma palavra: positivo ou negativo."},
        {"role": "human",   "content": estado["mensagem"]},
    ])
    valor = r.content.strip().lower()
    return {
        "sentimento": valor if valor in ("positivo", "negativo") else "negativo",
        "passos":     ["classificar"],
    }


def no_responder_positivo(estado: Estado) -> dict:
    r = llm.invoke([
        {"role": "system",  "content": "Responda de forma animada e encorajadora em 1 frase."},
        {"role": "human",   "content": estado["mensagem"]},
    ])
    return {"resposta": r.content.strip(), "passos": ["responder_positivo"]}


def no_responder_negativo(estado: Estado) -> dict:
    r = llm.invoke([
        {"role": "system",  "content": "Responda de forma empática e acolhedora em 1 frase."},
        {"role": "human",   "content": estado["mensagem"]},
    ])
    return {"resposta": r.content.strip(), "passos": ["responder_negativo"]}


# ─────────────────────────────────────────────
# 3. FUNÇÃO DE DECISÃO
# Lê o estado, retorna o nome do próximo nó.
# ─────────────────────────────────────────────
def decidir(estado: Estado) -> str:
    return "responder_positivo" if estado["sentimento"] == "positivo" else "responder_negativo"


# ─────────────────────────────────────────────
# 4. GRAFO
# ─────────────────────────────────────────────
grafo = StateGraph(Estado)

grafo.add_node("classificar",         no_classificar)
grafo.add_node("responder_positivo",  no_responder_positivo)
grafo.add_node("responder_negativo",  no_responder_negativo)

grafo.add_edge(START, "classificar")

grafo.add_conditional_edges(
    "classificar",
    decidir,
    {
        "responder_positivo": "responder_positivo",
        "responder_negativo": "responder_negativo",
    },
)

grafo.add_edge("responder_positivo", END)
grafo.add_edge("responder_negativo", END)

app = grafo.compile()


# ─────────────────────────────────────────────
# 5. EXECUÇÃO
# ─────────────────────────────────────────────
while True:
    msg = input("> ").strip()
    if not msg or msg.lower() == "sair":
        break

    resultado = app.invoke({
        "mensagem":   msg,
        "sentimento": "",
        "resposta":   "",
        "passos":     [],
    })

    print(f"Sentimento : {resultado['sentimento']}")
    print(f"Resposta   : {resultado['resposta']}")
    print(f"Passos     : {resultado['passos']}\n")
