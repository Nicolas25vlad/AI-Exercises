"""Classe responsável por filtrar o ruído da conversa entre a LLM e o usuário, removendo informações irrelevantes ou redundantes."""

from groq import Groq
import os
import re
import json
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

# Inicializa cliente Groq diretamente
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def evaluate_response(user_input: str, model_response: str) -> float:
    """
    Avalia a resposta do modelo em relação à entrada do usuário.
    Retorna um score de 0 a 10.
    """
    try:
        if len(model_response.split()) < 10:
            return 8.0
        
        prompt = f"""
        Avalie a qualidade da resposta abaixo para a pergunta feita.
        
        PERGUNTA: {user_input}
        
        RESPOSTA: {model_response}
        
        Atribua uma nota de 0 a 10 baseada em:
        - Relevância (0-10): A resposta responde diretamente à pergunta?
        - Clareza (0-10): É clara e objetiva?
        - Completude (0-10): Cobre os aspectos principais?
        
        Responda APENAS com um número (ex: 8.5).
        Nota:
        """
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=10
        )
        
        texto = response.choices[0].message.content.strip() #type: ignore
        numeros = re.findall(r'\d+\.?\d*', texto)
        
        if numeros:
            score = float(numeros[0])
            return min(10.0, max(0.0, score))
        else:
            return 5.0
            
    except Exception as e:
        print(f"Erro na avaliação: {e}")
        return 5.0


def avaliar_sentencas(pergunta: str, sentencas: list, max_sentencas: int = 10) -> list:
    """Avalia cada sentença individualmente e retorna com scores"""
    sentencas_com_scores = []
    sentencas_para_avaliar = sentencas[:max_sentencas]
    
    for sentenca in sentencas_para_avaliar:
        score = evaluate_response(pergunta, sentenca)
        sentencas_com_scores.append({
            "sentenca": sentenca,
            "score": score
        })
    
    sentencas_com_scores.sort(key=lambda x: x['score'], reverse=True)
    return sentencas_com_scores


def filtrar_sentencas_irrelevantes(pergunta: str, resposta: str, threshold: float = 6.0) -> str:
    """
    Filtra sentenças com score abaixo do threshold.
    Retorna apenas a resposta filtrada (string).
    """
    sentencas = re.split(r'[.!?]+', resposta)
    sentencas = [s.strip() for s in sentencas if s.strip() and len(s.split()) > 3]
    
    if not sentencas or len(sentencas) <= 2:
        return resposta
    
    sentencas_avaliadas = avaliar_sentencas(pergunta, sentencas)
    
    sentencas_relevantes = [
        s['sentenca'] for s in sentencas_avaliadas 
        if s['score'] >= threshold
    ]
    
    if not sentencas_relevantes:
        sentencas_relevantes = [sentencas_avaliadas[0]['sentenca']]
    
    if len(sentencas_relevantes) < 2 and len(sentencas) > 3:
        sentencas_relevantes = [
            sentencas_avaliadas[0]['sentenca'],
            sentencas_avaliadas[1]['sentenca']
        ]
    
    return ". ".join(sentencas_relevantes) + "."


def filtrar_resposta_por_sentencas(resposta: str, pergunta: str, threshold: float = 6.0) -> Dict[str, Any]:
    """
    Filtra resposta removendo sentenças irrelevantes.
    Retorna a resposta limpa e metadados separados.
    
    Args:
        resposta: A resposta gerada pelo modelo
        pergunta: A pergunta do usuário
        threshold: Score mínimo para manter uma sentença (0-10)
    
    Returns:
        dict: {
            'resposta_limpa': str,       # A resposta após o filtro (apenas o conteúdo)
            'filtro_aplicado': bool,     # Se o filtro foi aplicado
            'score_original': float,     # Score da resposta original
            'score_filtrado': float,     # Score da resposta filtrada
            'tokens_originais': int,     # Tokens da resposta original
            'tokens_filtrados': int,     # Tokens da resposta filtrada
            'tokens_salvos': int,        # Tokens economizados
            'sentencas_removidas': int,  # Sentenças removidas
            'acao': str                  # Ação realizada
        }
    """
    tokens_originais = len(resposta.split())
    
    # Se a resposta for curta, mantém
    if tokens_originais < 30:
        print("[filtro] Resposta curta, mantida original")
        return {
            'resposta_limpa': resposta,
            'filtro_aplicado': False,
            'score_original': 0.0,
            'score_filtrado': 0.0,
            'tokens_originais': tokens_originais,
            'tokens_filtrados': tokens_originais,
            'tokens_salvos': 0,
            'sentencas_removidas': 0,
            'acao': 'mantida_curta'
        }
    
    try:
        score_total = evaluate_response(pergunta, resposta)
        print(f"[filtro] Score total: {score_total:.1f}")
        
        # Se já for boa, mantém original
        if score_total >= threshold:
            print("[filtro] Resposta de qualidade, mantida original")
            return {
                'resposta_limpa': resposta,
                'filtro_aplicado': False,
                'score_original': score_total,
                'score_filtrado': score_total,
                'tokens_originais': tokens_originais,
                'tokens_filtrados': tokens_originais,
                'tokens_salvos': 0,
                'sentencas_removidas': 0,
                'acao': 'mantida_qualidade'
            }
        
        # Aplica filtro
        resposta_filtrada = filtrar_sentencas_irrelevantes(pergunta, resposta, threshold=5.0)
        tokens_filtrados = len(resposta_filtrada.split())
        
        # Se filtrou demais, mantém a original
        if tokens_filtrados < tokens_originais * 0.3:
            print("[filtro] Filtro removeu muitas sentenças, mantendo original")
            return {
                'resposta_limpa': resposta,
                'filtro_aplicado': False,
                'score_original': score_total,
                'score_filtrado': score_total,
                'tokens_originais': tokens_originais,
                'tokens_filtrados': tokens_originais,
                'tokens_salvos': 0,
                'sentencas_removidas': 0,
                'acao': 'mantida_agressiva'
            }
        
        score_filtrado = evaluate_response(pergunta, resposta_filtrada)
        sentencas_originais = len(re.split(r'[.!?]+', resposta))
        sentencas_filtradas = len(re.split(r'[.!?]+', resposta_filtrada))
        
        print(f"[filtro] Tokens salvos: {tokens_originais - tokens_filtrados}")
        
        return {
            'resposta_limpa': resposta_filtrada,
            'filtro_aplicado': True,
            'score_original': score_total,
            'score_filtrado': score_filtrado,
            'tokens_originais': tokens_originais,
            'tokens_filtrados': tokens_filtrados,
            'tokens_salvos': tokens_originais - tokens_filtrados,
            'sentencas_removidas': sentencas_originais - sentencas_filtradas,
            'acao': 'sentencas_filtradas'
        }
        
    except Exception as e:
        print(f"[filtro] ERRO: {e} - Mantendo resposta original")
        return {
            'resposta_limpa': resposta,
            'filtro_aplicado': False,
            'score_original': 0.0,
            'score_filtrado': 0.0,
            'tokens_originais': tokens_originais,
            'tokens_filtrados': tokens_originais,
            'tokens_salvos': 0,
            'sentencas_removidas': 0,
            'acao': 'erro'
        }