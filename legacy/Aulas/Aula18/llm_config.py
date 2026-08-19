#docker exec -it gemma-ia ollama pull gemma:2b
# type: ignore
from dotenv import load_dotenv
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent
from langchain_groq import ChatGroq
from pg_tools import TOOLS
from faq_tools import carregar_faq
from prompts import (
    ROUTER_PROMPT_COMPLETO,
    FINANCEIRO_PROMPT_COMPLETO,
    AGENDA_PROMPT_COMPLETO,
    ORQUESTRADOR_PROMPT_COMPLETO,
    FAQ_PROMPT_COMPLETO,
)

from memory_tools import memory_tool
load_dotenv()




"""Configurações para o modelo de linguagem."""

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
    tools=[memory_tool],  # Adiciona a ferramenta de memória
)

faq_app = create_agent(
    model=llm_rapido,
    tools=[carregar_faq],
    system_prompt=FAQ_PROMPT_COMPLETO,
)