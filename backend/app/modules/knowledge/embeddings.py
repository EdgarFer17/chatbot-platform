"""Local multilingual text embedding service using FastEmbed."""
import logging
from typing import Sequence
import numpy as np

logger = logging.getLogger("chatbot-platform-embeddings")

EMBEDDING_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_DIMENSION = 384

import os

_model_instance = None


def get_embedding_model():
    global _model_instance
    if _model_instance is None:
        from fastembed import TextEmbedding
        logger.info("Carregando modelo de embeddings %s...", EMBEDDING_MODEL_NAME)
        cache_dir = os.environ.get("FASTEMBED_CACHE_DIR") or os.environ.get("FASTEMBED_CACHE_PATH")
        _model_instance = TextEmbedding(model_name=EMBEDDING_MODEL_NAME, cache_dir=cache_dir)
    return _model_instance


def generate_embeddings(texts: Sequence[str]) -> list[list[float] | None]:
    """Generate normalized 384-d vector embeddings for a list of texts."""
    clean_texts = [text.strip() if text and text.strip() else " " for text in texts]
    if not clean_texts:
        return []
    try:
        model = get_embedding_model()
        vectors = list(model.embed(clean_texts))
        return [vector.tolist() if hasattr(vector, "tolist") else list(vector) for vector in vectors]
    except Exception as error:
        logger.warning("Falha ao gerar embeddings: %s. Prosseguindo sem vetor.", error)
        return [None] * len(clean_texts)


def generate_query_embedding(query: str) -> list[float] | None:
    """Generate 384-d vector embedding for a search query."""
    cleaned = query.strip()
    if not cleaned:
        return None
    try:
        model = get_embedding_model()
        vectors = list(model.embed([cleaned]))
        if vectors:
            v = vectors[0]
            return v.tolist() if hasattr(v, "tolist") else list(v)
    except Exception as error:
        logger.warning("Falha ao gerar embedding para consulta: %s", error)
    return None


def cosine_similarity(v1: Sequence[float] | None, v2: Sequence[float] | None) -> float:
    """Compute cosine similarity between two vectors."""
    if v1 is None or v2 is None or len(v1) == 0 or len(v2) == 0:
        return 0.0
    a = np.asarray(v1, dtype=np.float32)
    b = np.asarray(v2, dtype=np.float32)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))
