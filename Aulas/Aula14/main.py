#docker exec -it gemma-ia ollama pull gemma:2b
# type: ignore
from dotenv import load_dotenv
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent
from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import MemorySaver
from pg_tools import TOOLS
from faq_tools import carregar_faq
from prompts import (
    ROUTER_PROMPT_COMPLETO,
    FINANCEIRO_PROMPT_COMPLETO,
    AGENDA_PROMPT_COMPLETO,
    ORQUESTRADOR_PROMPT_COMPLETO,
    FAQ_PROMPT_COMPLETO,
)
from graph import FLUXO_AGENTES, set_apps
from guardrail import guardrail_entrada, guardrail_saida, anonimizar_entrada
from langchain.schema import RemoveMessages 

load_dotenv()

llm_gemini = ChatGoogleGenerativeAI(
    model = "gemini-3-flash-preview",
    temperature=0.7,
    top_p=0.95,
    api_key=os.getenv("GEMINI_API_KEY")
)

llm_groq = ChatGroq(
    model="mixtral-8x7b-32768",
    temperature=0.7,
    api_key=os.getenv("GROQ_API_KEY"),
)

llm_especialista = llm_gemini.with_fallbacks([llm_groq])

llm_rapido = ChatGroq (
    model="llama-3.3-70b-versatile",
    temperature=0.0,
    api_key=os.getenv("GROQ_API_KEY"),
)

router_app = create_agent(
    model=llm_rapido,
    system_prompt=ROUTER_PROMPT_COMPLETO,
)

financeiro_app = create_agent(
    model=llm_especialista,
    tools=TOOLS,
    system_prompt=FINANCEIRO_PROMPT_COMPLETO,
)

agenda_app = create_agent(
    model=llm_especialista,
    system_prompt=AGENDA_PROMPT_COMPLETO,
)

orquestrador_app = create_agent(
    model=llm_rapido,
    system_prompt=ORQUESTRADOR_PROMPT_COMPLETO,
)

faq_app = create_agent(
    model=llm_rapido,
    tools=[carregar_faq],
    system_prompt=FAQ_PROMPT_COMPLETO,
)

set_apps(router_app, financeiro_app, agenda_app, faq_app, orquestrador_app)

def executar_fluxo_acessor(pergunta_usuario: str, session_id: str) -> str:
    # Estado inicial com MessagesState
    estado_inicial = {
        "messages": [{"role": "human", "content": pergunta_usuario}],
        "session_id": session_id,
        "agentes_chamados": [],
        "rota": "",
        "saida_especialista": "",
    }

    estado_final = FLUXO_AGENTES.invoke(
        estado_inicial,
        config={"configurable": {"thread_id": session_id}},
    )

    print(f"[debug] agentes chamados: {estado_final['agentes_chamados']}")
    
    # Pega a última mensagem do assistente (pode ser dict ou AIMessage)
    messages = estado_final.get("messages", [])
    resposta = ""
    for msg in reversed(messages):
        # Tenta diferentes formatos de mensagem
        if hasattr(msg, 'content') and msg.content:  # AIMessage object
            resposta = msg.content
            break
        elif isinstance(msg, dict) and msg.get("role") == "assistant":  # dict format
            resposta = msg.get("content", "")
            break
        elif isinstance(msg, dict) and msg.get("type") == "ai":  # outro formato
            resposta = msg.get("content", "")
            break
    
    return resposta if resposta else "Não foi possível obter uma resposta."


while True:
    user_input = input("> ")
    if user_input.lower() in ["sair", "exit", "quit"]:
        print("Encerrando a conversa. Até mais!")
        break
    
    try:
        print(executar_fluxo_acessor(user_input, "sessao_teste"))
    except Exception as e:
        print(f"Erro: {e}")