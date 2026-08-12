import os
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain.tools import tool
from langchain_google_genai import GoogleGenerativeAIEmbeddings
load_dotenv()

PDF_PATH = os.getenv("PDF_PATH_FAQ")

@tool("carregar_faq", return_direct=False)
def carregar_faq(question: str) -> str:
    """Carrega e busca informações no FAQ."""
    loader = PyPDFLoader(PDF_PATH)
    documents = loader.load()

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    texts = text_splitter.split_documents(documents)

    embeddings = GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-2-preview",
        google_api_key=os.getenv("GEMINI_API_KEY")
    )

    vectorstore = FAISS.from_documents(texts, embeddings)
    results = vectorstore.similarity_search(question, k=3)
    return results