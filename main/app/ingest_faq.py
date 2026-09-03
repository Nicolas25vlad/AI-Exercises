"""
Script de ingestão do FAQ no Qdrant.

Lê o PDF, faz split em chunks, gera embeddings e insere na collection
"faq_chunks" do Qdrant.

A ingestão só acontece se o PDF tiver sido alterado desde a última execução.

Executar com:

    python -m app.ingest_faq
"""

import json
import os
import uuid
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import models

from app.config import FAQ_PDF_PATH
from app.vectorstore import (
    qdrant,
    gerar_embeddings_batch,
    COLLECTION_FAQ,
)


CHUNK_SIZE = 700
CHUNK_OVERLAP = 150
BATCH_SIZE = 5

METADATA_PATH = Path(__file__).with_name(".faq_ingest_metadata.json")


def obter_metadata_arquivo() -> dict:
    """
    Retorna informações do arquivo usadas para detectar alterações.
    """

    stat = os.stat(FAQ_PDF_PATH)

    return {
        "path": str(Path(FAQ_PDF_PATH).resolve()),
        "mtime_ns": stat.st_mtime_ns,
        "size": stat.st_size,
    }


def carregar_metadata_anterior() -> dict | None:
    """
    Carrega a metadata salva na última ingestão.
    """

    if not METADATA_PATH.exists():
        return None

    try:
        with METADATA_PATH.open("r", encoding="utf-8") as arquivo:
            return json.load(arquivo)
    except (json.JSONDecodeError, OSError):
        return None


def salvar_metadata(metadata: dict) -> None:
    """
    Salva a metadata do PDF após uma ingestão bem-sucedida.
    """

    with METADATA_PATH.open("w", encoding="utf-8") as arquivo:
        json.dump(metadata, arquivo, indent=2, ensure_ascii=False)


def faq_foi_alterado() -> bool:
    """
    Verifica se o PDF mudou desde a última ingestão.
    """

    metadata_atual = obter_metadata_arquivo()
    metadata_anterior = carregar_metadata_anterior()

    if metadata_anterior is None:
        print("[ingest] Nenhuma ingestão anterior encontrada.")
        return True

    if metadata_atual != metadata_anterior:
        print("[ingest] Alteração detectada no FAQ.")
        return True

    print("[ingest] FAQ não foi alterado desde a última ingestão.")
    return False


def ingerir_faq(forcar: bool = False) -> int:
    """
    Indexa o PDF do FAQ no Qdrant.

    Retorna o número de chunks inseridos.

    Se o arquivo não tiver sido alterado, não faz nada.
    """

    if not Path(FAQ_PDF_PATH).exists():
        raise FileNotFoundError(
            f"PDF do FAQ não encontrado: {FAQ_PDF_PATH}"
        )

    if not forcar and not faq_foi_alterado():
        print("[ingest] Pulando ingestão.")
        return 0

    metadata_atual = obter_metadata_arquivo()

    print(f"[ingest] Carregando PDF: {FAQ_PDF_PATH}")

    loader = PyPDFLoader(str(FAQ_PDF_PATH))
    docs = loader.load()

    print(f"[ingest] {len(docs)} página(s) carregada(s)")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )

    chunks = splitter.split_documents(docs)

    print(f"[ingest] {len(chunks)} chunk(s) gerado(s)")

    info = qdrant.get_collection(COLLECTION_FAQ)

    if info.points_count > 0:
        print(
            f"[ingest] Limpando "
            f"{info.points_count} ponto(s) existente(s)..."
        )

        qdrant.delete(
            collection_name=COLLECTION_FAQ,
            points_selector=models.FilterSelector(
                filter=models.Filter(must=[])
            ),
        )

    textos = [chunk.page_content for chunk in chunks]

    for i in range(0, len(textos), BATCH_SIZE):
        lote_textos = textos[i : i + BATCH_SIZE]
        lote_chunks = chunks[i : i + BATCH_SIZE]

        print(
            f"[ingest] Gerando embeddings para chunk "
            f"{i + 1}–{i + len(lote_textos)}..."
        )

        vetores = gerar_embeddings_batch(lote_textos)

        pontos = [
            models.PointStruct(
                id=str(uuid.uuid4()),
                vector=vetor,
                payload={
                    "page_content": chunk.page_content,
                    "page_number": chunk.metadata.get("page", 0),
                    "source": str(
                        chunk.metadata.get("source", "")
                    ),
                    "faq_mtime_ns": metadata_atual["mtime_ns"],
                    "faq_size": metadata_atual["size"],
                },
            )
            for vetor, chunk in zip(vetores, lote_chunks)
        ]

        qdrant.upsert(
            collection_name=COLLECTION_FAQ,
            points=pontos,
        )

    # IMPORTANTE:
    # só registra a nova versão depois que toda a ingestão terminou.
    salvar_metadata(metadata_atual)

    print(
        f"[ingest] Concluído! "
        f"{len(chunks)} chunk(s) indexado(s) no Qdrant."
    )

    return len(chunks)


if __name__ == "__main__":
    ingerir_faq()