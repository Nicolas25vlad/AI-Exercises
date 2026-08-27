"""
Tool de memória de longo prazo — consulta conversas ANTERIORES do usuário.

Migração de tool_mongodb.py (raiz) para dentro de app/tools/.
"""

from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig

from app.memory import recuperar_historico

# ==============================================================================
# POR QUE user_id E NÃO session_id
# ------------------------------------------------------------------------------
# O front gera um UUID novo a cada "nova sessão". Esse UUID é a CONVERSA
# (vira thread_id do checkpointer). Se buscarmos conversas anteriores por ele,
# o resultado é sempre vazio: cada conversa tem um id diferente da anterior.
#
# Para achar o passado precisamos de um identificador ESTÁVEL do usuário —
# o user_id. Enquanto o front não mandar um, o fallback para thread_id mantém
# a tool funcionando (e é o suficiente para testar com um id fixo à mão).
# ==============================================================================


@tool
def buscar_historico(busca: str, config: RunnableConfig) -> str:
    """Consulta conversas ANTERIORES do usuário (sessões já encerradas).

    Use SOMENTE quando a resposta depende de algo dito numa conversa passada
    — preferências, decisões ou planos que o usuário mencionou antes.
    NÃO use para dados que estão no banco (gastos, saldos, eventos): para isso
    já existem as tools de consulta específicas como query_transactions,
    total_balance, daily_balance.

    Args:
        busca: assunto a procurar nos resumos das conversas anteriores.
    """
    configuravel = (config or {}).get("configurable", {})
    user_id      = configuravel.get("user_id") or configuravel.get("thread_id")

    if not user_id:
        return "Não foi possível identificar o usuário para buscar o histórico."

    historico = recuperar_historico(user_id, busca=busca, limite=3)

    if not historico:
        return "Nenhuma conversa anterior relevante encontrada."

    return "\n\n".join(
        f"[{h['iniciada_em']:%d/%m/%Y}] {h['resumo']}" for h in historico
    )


TOOLS_MEMORIA = [buscar_historico]