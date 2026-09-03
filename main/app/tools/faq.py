from langchain.tools import tool
from app.vectorstore import qdrant, gerar_embedding, COLLECTION_FAQ


@tool
def faq_retriever(question: str) -> str:
    """Busca no FAQ oficial os trechos mais relevantes para responder a pergunta."""
    vetor = gerar_embedding(question)

    resultados = qdrant.query_points(
        collection_name=COLLECTION_FAQ,
        query=vetor,
        limit=6,
    )

    if not resultados.points:
        return "Nenhum trecho relevante encontrado no FAQ."

    return "\n\n".join(
        ponto.payload["page_content"] for ponto in resultados.points
    )