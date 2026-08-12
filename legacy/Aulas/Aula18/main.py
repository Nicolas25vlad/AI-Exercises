#docker exec -it gemma-ia ollama pull gemma:2b
# type: ignore
from graph import FLUXO_AGENTES, set_apps
from guardrail import guardrail_entrada, guardrail_saida, anonimizar_entrada
from memory_mongodb import iniciar_sessao, salvar_mensagem, encerrar_sessao
from llm_config import router_app, financeiro_app, agenda_app, faq_app, orquestrador_app
from noise_filter import filtrar_resposta_por_sentencas



set_apps(router_app, financeiro_app, agenda_app, faq_app, orquestrador_app)

def executar_fluxo_acessor(pergunta_usuario: str, session_id: str) -> str:
    salvar_mensagem(session_id, "usuario", pergunta_usuario)
    # Anonimizar a entrada antes de qualquer verificação
    mensagem_anonimizada, mapa_pii = anonimizar_entrada(pergunta_usuario)
    
    # Aplicar guardrail de entrada (validação de segurança)
    verificacao = guardrail_entrada(mensagem_anonimizada)
    
    if verificacao["bloqueado"]:
        resposta_bloqueada = f"[BLOQUEADO] {verificacao['mensagem']}"
        salvar_mensagem(session_id, "assistente", resposta_bloqueada)
        return resposta_bloqueada
    
    # Estado inicial com MessagesState
    estado_inicial = {
        "messages": [{"role": "human", "content": mensagem_anonimizada}],
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
        if hasattr(msg, 'content') and msg.content:
            resposta = msg.content
            break
        elif isinstance(msg, dict) and msg.get("role") == "assistant":
            resposta = msg.get("content", "")
            break
        elif isinstance(msg, dict) and msg.get("type") == "ai":
            resposta = msg.get("content", "")
            break
    
    resposta_final = resposta if resposta else "Não foi possível obter uma resposta."
    
    # Aplicar guardrail de saída (compliance e remoção de PII)
    saida_revisada = guardrail_saida(resposta_final, mapa_pii, restaurar_pii=False)
    resposta_usuario = saida_revisada["conteudo"]

   

    # Aplicar filtro de ruído
    resposta_filtrada = filtrar_resposta_por_sentencas(resposta_usuario, pergunta_usuario)['resposta_limpa']
    
    salvar_mensagem(session_id, "assistente", resposta_filtrada)
    return resposta_usuario

session_id = "sessao_teste"
iniciar_sessao(session_id)

try:
    while True:
        user_input = input("> ")
        if user_input.lower() in ["sair", "exit", "quit"]:
            encerrar_sessao(session_id)
            print("Encerrando a conversa. Até mais!")
            break
        
        try:
            print(executar_fluxo_acessor(user_input, "sessao_teste"))
        except Exception as e:
            print(f"Erro: {e}")
            
except KeyboardInterrupt:
    print("\nEncerrando a conversa. Até mais!")
    encerrar_sessao(session_id)