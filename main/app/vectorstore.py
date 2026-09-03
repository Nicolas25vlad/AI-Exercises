"""
Cliente Qdrant e função de embedding — centralizados aqui.

Dois consumidores:
  - memory.py   → salva/busca resumos na collection "memoria_resumos"
  - tools/faq.py → busca chunks do PDF na collection "faq_chunks"

O modelo de embedding é o mesmo para ambos (gemini-embedding-2-preview, 768d),
então instanciamos uma vez só.
"""

from qdrant_client import QdrantClient, models
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from app.config import QDRANT_URL, QDRANT_API_KEY, GEMINI_API_KEY

qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

COLLECTION_MEMORIA = "memoria_resumos"
COLLECTION_FAQ     = "faq_chunks"
EMBEDDING_DIM      = 768

_embeddings = GoogleGenerativeAIEmbeddings(
    model="gemini-embedding-2-preview",
    google_api_key=GEMINI_API_KEY,
)


def gerar_embedding(texto: str) -> list[float]:
    """Gera um vetor de 768 dimensões para o texto informado."""
    return _embeddings.embed_query(texto, output_dimensionality=EMBEDDING_DIM)


def gerar_embeddings_batch(textos: list[str]) -> list[list[float]]:
    """Gera embeddings para uma lista de textos de uma vez (mais eficiente)."""
    return _embeddings.embed_documents(textos, output_dimensionality=EMBEDDING_DIM)