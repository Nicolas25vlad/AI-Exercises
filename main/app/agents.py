from langchain.agents import create_agent

from app.llms import llm_especialista, llm_rapido
from app.prompts import (
    AGENDA_PROMPT_COMPLETO,
    FAQ_PROMPT_COMPLETO,
    FINANCEIRO_PROMPT_COMPLETO,
    ORQUESTRADOR_PROMPT_COMPLETO,
    ROUTER_PROMPT_COMPLETO,
)
from app.tools.faq import faq_retriever
from app.tools.memoria import TOOLS_MEMORIA
from langchain_core.runnables import RunnableConfig
from app.tools.financeiro import TOOLS

TOOLS_AGENDA = []

router_app = create_agent(
    model=llm_rapido, 
    tools=TOOLS_MEMORIA,
    system_prompt=ROUTER_PROMPT_COMPLETO
    )


financeiro_app = create_agent(
    model=llm_especialista,
    tools=TOOLS+TOOLS_MEMORIA,
    system_prompt=FINANCEIRO_PROMPT_COMPLETO,
)
agenda_app = create_agent(
    model=llm_especialista,
    tools=TOOLS_AGENDA+TOOLS_MEMORIA,
    system_prompt=AGENDA_PROMPT_COMPLETO,
)
orquestrador_app = create_agent(
    model=llm_rapido,
    system_prompt=ORQUESTRADOR_PROMPT_COMPLETO,
)
faq_app = create_agent(
    model=llm_rapido,
    tools=[faq_retriever],
    system_prompt=FAQ_PROMPT_COMPLETO,
)
