from sentence_transformers import SentenceTransformer
from typing import List, Optional
import numpy as np
from app.core.config import settings


class EmbeddingService:
    """Service for generating text embeddings using sentence-transformers."""
    
    _model: Optional[SentenceTransformer] = None
    
    @classmethod
    def get_model(cls) -> SentenceTransformer:
        """Lazy-load the embedding model."""
        if cls._model is None:
            cls._model = SentenceTransformer(settings.EMBEDDING_MODEL)
        return cls._model
    
    @classmethod
    def generate_embedding(cls, text: str) -> List[float]:
        """Generate embedding for a single text."""
        model = cls.get_model()
        embedding = model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    @classmethod
    def generate_embeddings(cls, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        model = cls.get_model()
        embeddings = model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()
    
    @classmethod
    def create_product_text(cls, title: str, authors: List[str], annotation: Optional[str] = None) -> str:
        """Create concatenated text for product embedding."""
        authors_text = ", ".join(authors) if authors else ""
        parts = [title]
        if authors_text:
            parts.append(f"by {authors_text}")
        if annotation:
            parts.append(annotation)
        return " ".join(parts)
