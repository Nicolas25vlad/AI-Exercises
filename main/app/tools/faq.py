from functools import lru_cache

from langchain.tools import tool
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import FAQ_PDF_PATH, GEMINI_API_KEY


@lru_cache(maxsize=1)
def _get_retriever():
    documents = PyPDFLoader(str(FAQ_PDF_PATH)).load()
    texts = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
    ).split_documents(documents)
    embeddings = GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-2-preview",
        google_api_key=GEMINI_API_KEY,
    )
    return FAISS.from_documents(texts, embeddings).as_retriever(search_kwargs={"k": 3})


@tool("faq_retriever", return_direct=False)
def faq_retriever(question: str) -> str:
    """Busca no FAQ oficial a informação relevante para a pergunta."""
    documents = _get_retriever().invoke(question)
    return "\n\n".join(document.page_content for document in documents)
