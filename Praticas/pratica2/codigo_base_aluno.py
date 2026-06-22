from dotenv import load_dotenv
import os
import re
from pymongo import MongoClient
from langchain.agents import create_agent
from langchain_groq import ChatGroq
from langchain.tools import tool

load_dotenv()

# ======================================================
# LLM
# ======================================================

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.3,
    api_key=os.getenv("GROQ_API_KEY"),
)


# ======================================================
# MONGODB
# ======================================================
client = MongoClient("mongodb://localhost:27017")
db = client["friboi_pratica"]
collection = db["receitas_pratica"]

# ======================================================
# AGENTE VERIFICADOR — JÁ PRONTO, NÃO ALTERE
# ======================================================
PERSONA_SISTEMA = """
Você é o Chef Friboi, assistente culinário simpático e especialista em 
carnes bovinas da Friboi. Você sempre responde em português, com tom 
amigável e profissional, ajudando os usuários a encontrar receitas e 
dicas para cortes de carne.
"""

VERIFICADOR_PROMPT = f"""
{PERSONA_SISTEMA}


### PAPEL:
Sua ÚNICA responsabilidade é analisar a mensagem do usuário e determinar
qual corte de carne ele deseja. Você NÃO sugere receitas, NÃO dá dicas
de preparo e NÃO responde perguntas fora do tema de cortes. Quando encontrar um corte válido, encaminhe para o agente gerador.


### REGRAS:
1. Se o usuário mencionar um corte válido da lista, responda APENAS com:
   CORTE=[nome_do_corte]
   Não adicione nenhum texto antes ou depois.
2. Se o usuário mencionar um corte que NÃO está na lista de cortes válidos
   (ex: carne de avestruz, carne de jacaré, cordeiro, porco), responda educadamente que não tem esse corte e tente identificar outro corte que ele deseja.
3. Se o usuário NÃO mencionar nenhum corte, interaja educadamente para
   tentar identificar qual corte ele deseja. Faça perguntas curtas e
   objetivas, sugerindo opções da lista.
4. Se for uma saudação ou conversa casual (oi, bom dia, tudo bem),
   responda de forma simpática e aproveite para perguntar qual corte
   de carne o usuário gostaria de preparar hoje.
5. NUNCA invente cortes que não foram mencionados pelo usuário.
6. Responda SEMPRE em português.


### CORTES VÁLIDOS:
acém, alcatra, capa do filé, contrafilé, costela, coxão duro,
coxão mole, filé mignon, fraldinha, lagarto, maminha, miúdos,
músculo, paleta, patinho, peito, picanha, ponta do contrafilé.


### PROTOCOLO DE ENCAMINHAMENTO:
CORTE=[nome_do_corte]
"""

VERIFICADOR_SHOTS_OPEN = (
    "A seguir estão EXEMPLOS ILUSTRATIVOS do comportamento esperado. "
    "Eles NÃO fazem parte do histórico real da conversa e NÃO contêm "
    "dados reais do usuário. "
    "Ignore os valores fictícios presentes nesses exemplos."
)

VERIFICADOR_SHOT_1 = """
usuario: Quero uma receita com picanha
verificador: CORTE=picanha
"""

VERIFICADOR_SHOT_2 = """
usuario: Oi, tudo bem?
verificador: Oi! Tudo ótimo por aqui! Estou pronto para te ajudar \
a escolher um corte de carne. O que você gostaria de preparar hoje? \
Temos opções como picanha, fraldinha, costela, filé mignon e muito mais!
"""

VERIFICADOR_SHOT_3 = """
usuario: Quero fazer algo especial para o jantar
verificador: Que legal! Para te ajudar, preciso saber qual corte de \
carne você prefere. Algumas sugestões: picanha e filé mignon são ótimos \
para ocasiões especiais, ou talvez uma costela assada? Qual desses te \
agrada mais?
"""

VERIFICADOR_SHOTS_CUT = (
    "FIM DOS EXEMPLOS. "
    "Considere apenas as mensagens abaixo como contexto verdadeiro."
)

VERIFICADOR_PROMPT_COMPLETO = (
    VERIFICADOR_PROMPT     + "\n\n" +
    VERIFICADOR_SHOTS_OPEN + "\n\n" +
    VERIFICADOR_SHOT_1     + "\n\n" +
    VERIFICADOR_SHOT_2     + "\n\n" +
    VERIFICADOR_SHOT_3     + "\n\n" +
    VERIFICADOR_SHOTS_CUT
)

verificador_app = create_agent(
    model=llm,
    system_prompt=VERIFICADOR_PROMPT,
)



historico_receitas = {}

@tool
def buscar_receita(corte: str, session_id: str = "default") -> str:
    """Busca uma receita ou dica no MongoDB para o corte informado, sem repetir."""
    regex = re.compile(corte, re.IGNORECASE)
    chave = f"{session_id}_{corte.lower()}"  # <-- chave separada por corte
    ja_mostrados = historico_receitas.get(chave, [])

    doc = collection.find_one({
        "Corte": {"$regex": regex},
        "Tipo": "Receita",
        "_id": {"$nin": ja_mostrados}
    })

    if not doc:
        doc = collection.find_one({
            "Corte": {"$regex": regex},
            "_id": {"$nin": ja_mostrados}
        })

    if not doc:
        total = collection.count_documents({"Corte": {"$regex": regex}})
        return "SEM_MAIS_RECEITAS" if total > 0 else "NAO_ENCONTRADO"

    historico_receitas.setdefault(chave, []).append(doc["_id"])

    return f"""Título: {doc.get('Título', '')}
Ingredientes: {doc.get('Ingredientes', 'Não informado')}
Modo de preparo: {doc.get('Modo de preparo', 'Não informado')}
Tipo: {doc.get('Tipo', '')}"""

GERADOR_PROMPT = f"""
{PERSONA_SISTEMA}

### PAPEL:
Você recebe um corte no formato CORTE=<nome> e usa a tool buscar_receita para encontrar receitas.

### REGRAS:
1. Sempre use a tool buscar_receita antes de responder.
2. Se retornar NAO_ENCONTRADO, informe que não há receitas e sugira: picanha, costela, fraldinha, alcatra.
3. Se retornar SEM_MAIS_RECEITAS, informe que só havia essa receita disponível para o corte.
4. Apresente a receita de forma organizada e simpática.
5. Responda sempre em português.
6. Ao final pergunte se quer outra receita ou outro corte.
"""

gerador_app = create_agent(
    model=llm,
    tools=[buscar_receita],
    system_prompt=GERADOR_PROMPT,
)



# ======================================================
# FLUXO DOS AGENTES 
# ======================================================
ultimo_corte = {}  # session_id -> corte

def executar_fluxo(pergunta_usuario: str, session_id: str) -> str:
    if any(p in pergunta_usuario.lower() for p in ["outro corte", "mudar corte", "trocar corte"]):
        historico_receitas.pop(session_id, None)

    # Se pedir outra receita do mesmo corte, pula o verificador
    if any(p in pergunta_usuario.lower() for p in ["outra", "outro", "mais uma", "não gostei"]):
        corte_nome = ultimo_corte.get(session_id)
        if corte_nome:
            saida_gerador = gerador_app.invoke(
                {"messages": [{"role": "human", "content": f"CORTE={corte_nome} session_id={session_id}_{corte_nome}"}]},
                config={"configurable": {"thread_id": f"{session_id}_{corte_nome}"}},
            )
            return saida_gerador["messages"][-1].text.strip()

    saida_verificador = verificador_app.invoke(
        {"messages": [{"role": "human", "content": pergunta_usuario}]},
        config={"configurable": {"thread_id": session_id}},
    )
    resultado = saida_verificador["messages"][-1].text.strip()

    if not resultado.startswith("CORTE="):
        return resultado

    corte_nome = resultado.replace("CORTE=", "").strip()
    ultimo_corte[session_id] = corte_nome  # salva o último corte

    saida_gerador = gerador_app.invoke(
        {"messages": [{"role": "human", "content": f"CORTE={corte_nome} session_id={session_id}_{corte_nome}"}]},
        config={"configurable": {"thread_id": f"{session_id}_{corte_nome}"}},
    )
    return saida_gerador["messages"][-1].text.strip()

if __name__ == "__main__":
    print("🥩 Chef Friboi no ar! Digite 'sair' para encerrar.\n")
    while True:
        try:
            user_input = input("> ")
            if user_input.lower() in ("sair", "exit", "fim", "tchau"):
                print("Até a próxima! Bom apetite! 👋")
                break
            resposta = executar_fluxo(user_input, session_id="usuario_01")
            print(f"\n🧑‍🍳 {resposta}\n")
        except Exception as e:
            print(f"Erro: {e}")
            continue