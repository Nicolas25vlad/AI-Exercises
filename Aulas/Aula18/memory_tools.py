from langchain.tools import tool
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_nvidia import ChatNVIDIA
from pymongo import MongoClient
import os
import faiss
import numpy as np
from typing import List, Dict

"""
=================
TOOLS PARA SISTEMA DE MEMORIA VIA EMBEDDINGS
---------
"""

load_dotenv()

_mongo = MongoClient(os.getenv("MONGODB_URI", "mongodb://localhost:27017"))
db = _mongo["assessor"]
col_sessoes = db["sessoes"]


def memory_loader(session_id: str) -> List[Dict]:
    """
    Retorna as mensagens da sessão ativa, ordenadas por data.
    """
    try:
        doc = col_sessoes.find_one({"session_id": session_id})
        if not doc:
            return []
        mensagens = doc.get("mensagens", [])
        return sorted(mensagens, key=lambda x: x.get("timestamp", ""))
    except Exception as e:
        print(f"Erro ao carregar memória: {e}")
        return []


def memory_retriever(mensagens: List[Dict]) -> str:
    """
    Usa o combo LLM NVIDIA(EMBEDDINGS) para busca + LLM GROQ para gerar o resumo.
    """
    # Inicializar LLMs
    llm_nvidia = ChatNVIDIA(
        model="nvidia-embeddings-3-large",
        api_key=os.getenv("NVIDIA_API_KEY"),
    )

    _llm_resumo = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0.0,
        api_key=os.getenv("GROQ_API_KEY"), # type: ignore
    )

    # 1. Extrair os textos (verificando se a chave existe)
    textos = []
    for item in mensagens:
        text = item.get("text", "")
        if text and isinstance(text, str):
            textos.append(text)
    
    if not textos:
        return "Nenhum texto válido encontrado para processar."
    
    # 2. Gerar embeddings
    try:
        embeddings = llm_nvidia.embed_documents(textos) # type: ignore
        if embeddings is None or len(embeddings) == 0:
            return "Erro ao gerar embeddings para os textos."
    except Exception as e:
        return f"Erro ao gerar embeddings: {str(e)}"
    
    # 3. Criar índice FAISS para busca eficiente
    try:
        embedding_dim = len(embeddings[0])
        index = faiss.IndexFlatL2(embedding_dim)
        embeddings_array = np.array(embeddings).astype('float32')
        index.add(embeddings_array) # type: ignore
    except Exception as e:
        return f"Erro ao criar índice FAISS: {str(e)}"
    
    # 4. Definir consulta para busca
    query = "Pontos principais e informações mais relevantes"
    try:
        query_embedding = llm_nvidia.embed_query(query) # type: ignore
        if query_embedding is None:
            return "Erro ao gerar embedding da consulta."
        query_embedding = np.array(query_embedding).astype('float32').reshape(1, -1)
    except Exception as e:
        return f"Erro ao gerar embedding da consulta: {str(e)}"
    
    # 5. Buscar os top-k mais similares (k=3)
    k = min(3, len(textos))
    try:
        distances, indices = index.search(query_embedding, k) # type: ignore
    except Exception as e:
        return f"Erro ao buscar documentos similares: {str(e)}"
    
    # 6. Montar contexto com os textos recuperados
    try:
        contextos_recuperados = [textos[idx] for idx in indices[0]]
        contexto = "\n\n---\n\n".join(contextos_recuperados)
        
        # Adicionar metadados se disponíveis
        if len(contextos_recuperados) < len(textos):
            contexto += f"\n\n(Nota: {len(contextos_recuperados)} de {len(textos)} mensagens foram selecionadas como mais relevantes)"
    except Exception as e:
        return f"Erro ao montar contexto: {str(e)}"
    
    # 7. Gerar resumo com o LLM
    prompt = f"""
    Você é um assistente especializado em resumir conversas e extrair informações chave.
    
    Contexto (mensagens mais relevantes da conversa):
    {contexto}
    
    Instruções:
    1. Crie um resumo conciso e bem estruturado
    2. Destaque os pontos mais importantes discutidos
    3. Mantenha as informações essenciais
    4. Organize em tópicos se necessário
    5. Seja objetivo e claro
    
    Resumo:
    """
    
    try:
        resposta = _llm_resumo.invoke(prompt)
        return resposta.content # type: ignore
    except Exception as e:
        return f"Erro ao gerar resumo: {str(e)}"


@tool
def memory_tool(session_id: str) -> str:
    """
    Ferramenta para carregar e resumir a memória de uma sessão.
    
    Args:
        session_id (str): ID da sessão a ser resumida
    
    Returns:
        str: Resumo das conversas da sessão
    """
    if not session_id or not isinstance(session_id, str):
        return "Erro: session_id inválido ou não fornecido."
    
    mensagens = memory_loader(session_id)
    
    if not mensagens:
        return f"Nenhuma mensagem encontrada para a sessão {session_id}."
    
    return memory_retriever(mensagens)