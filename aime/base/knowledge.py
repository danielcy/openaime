from __future__ import annotations
import asyncio
from abc import ABC, abstractmethod
from typing import Any, Optional, List, Tuple
import uuid
import re
from collections import Counter


class BaseKnowledge(ABC):
    """Abstract base class for knowledge base systems."""

    @abstractmethod
    async def add_document(self, content: str, metadata: Optional[dict[str, Any]] = None) -> str:
        """Add a document to the knowledge base.

        Args:
            content: The content of the document to add.
            metadata: Optional metadata associated with the document.

        Returns:
            A unique identifier for the added document.
        """
        pass

    @abstractmethod
    async def search(self, query: str, top_k: int = 3) -> List[Tuple[str, float]]:
        """Search for relevant documents in the knowledge base.

        Args:
            query: The search query string.
            top_k: The maximum number of results to return.

        Returns:
            A list of (content, score) pairs sorted by relevance (descending).
        """
        pass

    @abstractmethod
    async def get_document(self, doc_id: str) -> Optional[str]:
        """Retrieve a document by its unique identifier.

        Args:
            doc_id: The unique identifier of the document to retrieve.

        Returns:
            The content of the document, or None if not found.
        """
        pass

    @abstractmethod
    async def delete_document(self, doc_id: str) -> bool:
        """Delete a document from the knowledge base.

        Args:
            doc_id: The unique identifier of the document to delete.

        Returns:
            True if the document was successfully deleted, False otherwise.
        """
        pass


class SimpleInMemoryKnowledge(BaseKnowledge):
    """A simple in-memory knowledge base implementation.

    Uses basic tokenization, bag-of-words representation, and cosine similarity
    for document search and retrieval.
    """

    def __init__(self):
        self._documents: dict[str, str] = {}
        self._metadata: dict[str, Optional[dict[str, Any]]] = {}
        self._vocabulary: set[str] = set()
        self._document_vectors: dict[str, dict[str, int]] = {}
        self._lock = asyncio.Lock()

    def _tokenize(self, text: str) -> list[str]:
        """Basic tokenization: lowercase, remove punctuation, split into words."""
        if not text:
            return []
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        tokens = text.split()
        return [token for token in tokens if len(token) > 0]

    def _compute_term_frequency(self, tokens: list[str]) -> dict[str, int]:
        """Compute term frequency for a list of tokens."""
        return dict(Counter(tokens))

    def _cosine_similarity(self, vec1: dict[str, int], vec2: dict[str, int]) -> float:
        """Compute cosine similarity between two vectors."""
        all_terms = set(vec1.keys()).union(set(vec2.keys()))

        dot_product = 0.0
        norm1 = 0.0
        norm2 = 0.0

        for term in all_terms:
            freq1 = vec1.get(term, 0)
            freq2 = vec2.get(term, 0)

            dot_product += freq1 * freq2
            norm1 += freq1 ** 2
            norm2 += freq2 ** 2

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 ** 0.5 * norm2 ** 0.5)

    async def add_document(self, content: str, metadata: Optional[dict[str, Any]] = None) -> str:
        async with self._lock:
            doc_id = str(uuid.uuid4())
            self._documents[doc_id] = content
            self._metadata[doc_id] = metadata

            # Tokenize and compute vector
            tokens = self._tokenize(content)
            vector = self._compute_term_frequency(tokens)

            self._document_vectors[doc_id] = vector
            self._vocabulary.update(vector.keys())

            return doc_id

    async def search(self, query: str, top_k: int = 3) -> List[Tuple[str, float]]:
        async with self._lock:
            if not self._documents:
                return []

            # Tokenize and compute query vector
            query_tokens = self._tokenize(query)
            query_vector = self._compute_term_frequency(query_tokens)

            # Compute similarity with all documents
            similarities: list[Tuple[str, float]] = []
            for doc_id, doc_vector in self._document_vectors.items():
                score = self._cosine_similarity(query_vector, doc_vector)
                if score > 0:
                    similarities.append((self._documents[doc_id], score))

            # Sort by score descending and take top_k
            similarities.sort(key=lambda x: x[1], reverse=True)
            return similarities[:top_k]

    async def get_document(self, doc_id: str) -> Optional[str]:
        async with self._lock:
            return self._documents.get(doc_id)

    async def get_metadata(self, doc_id: str) -> Optional[dict[str, Any]]:
        """Retrieve metadata for a document by its unique identifier.

        Args:
            doc_id: The unique identifier of the document to retrieve metadata for.

        Returns:
            The metadata for the document, or None if not found.
        """
        async with self._lock:
            return self._metadata.get(doc_id)

    async def delete_document(self, doc_id: str) -> bool:
        async with self._lock:
            if doc_id not in self._documents:
                return False

            del self._documents[doc_id]
            if doc_id in self._metadata:
                del self._metadata[doc_id]
            if doc_id in self._document_vectors:
                del self._document_vectors[doc_id]

            # Recompute vocabulary
            self._vocabulary.clear()
            for vector in self._document_vectors.values():
                self._vocabulary.update(vector.keys())

            return True


__all__ = [
    "BaseKnowledge",
    "SimpleInMemoryKnowledge",
]
