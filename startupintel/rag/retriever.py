"""FAISS-based RAG retriever with sentence-transformers embeddings."""

from __future__ import annotations

import os
import pickle
from pathlib import Path
from typing import TYPE_CHECKING

from startupintel.config import get_settings

if TYPE_CHECKING:
    import numpy as np
    from sentence_transformers import SentenceTransformer


class Document:
    """A document in the RAG corpus."""

    def __init__(self, id: str, text: str, metadata: dict | None = None):
        self.id = id
        self.text = text
        self.metadata = metadata or {}

    def to_dict(self) -> dict:
        return {"id": self.id, "text": self.text, "metadata": self.metadata}


class FAISSRetriever:
    """FAISS-based vector retriever for semantic search."""

    def __init__(
        self,
        model_name: str | None = None,
        index_path: str | None = None,
        top_k: int | None = None,
        similarity_threshold: float | None = None,
    ):
        self.model_name = model_name or get_settings().embedding_model
        self.index_path = index_path or get_settings().faiss_index_path
        self.top_k = top_k or get_settings().rag_top_k
        self.similarity_threshold = similarity_threshold or get_settings().rag_similarity_threshold

        self._model: SentenceTransformer | None = None
        self._index = None
        self._documents: list[Document] = []
        self._id_to_idx: dict[str, int] = {}

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        return self._model

    def _ensure_index(self):
        if self._index is None:
            import faiss

            dim = self.model.get_sentence_embedding_dimension()
            self._index = faiss.IndexFlatIP(dim)  # Inner product for cosine similarity with normalized vectors

    def encode(self, texts: list[str]) -> np.ndarray:
        import numpy as np

        embeddings = self.model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        return np.array(embeddings, dtype=np.float32)

    def add_documents(self, documents: list[Document]) -> None:
        """Add documents to the index."""
        if not documents:
            return

        self._ensure_index()

        texts = [doc.text for doc in documents]
        embeddings = self.encode(texts)

        start_idx = len(self._documents)
        for i, doc in enumerate(documents):
            self._id_to_idx[doc.id] = start_idx + i
            self._documents.append(doc)

        self._index.add(embeddings)

    async def search(self, query: str, top_k: int | None = None) -> list[dict]:
        """Search for similar documents."""
        k = top_k or self.top_k

        if self._index is None or self._index.ntotal == 0:
            return []

        query_embedding = self.encode([query])
        scores, indices = self._index.search(query_embedding, k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self._documents):
                continue
            if score < self.similarity_threshold:
                continue

            doc = self._documents[idx]
            results.append({
                "id": doc.id,
                "text": doc.text,
                "metadata": doc.metadata,
                "score": float(score),
                "similarity": float(score),
            })

        return results

    def save(self, path: str | None = None) -> None:
        """Save the index and documents to disk."""
        save_path = path or self.index_path
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)

        # Save FAISS index
        if self._index is not None:
            import faiss

            faiss.write_index(self._index, f"{save_path}.faiss")

        # Save documents and mapping
        with open(f"{save_path}.docs.pkl", "wb") as f:
            pickle.dump({
                "documents": [doc.to_dict() for doc in self._documents],
                "id_to_idx": self._id_to_idx,
            }, f)

    def load(self, path: str | None = None) -> bool:
        """Load the index and documents from disk."""
        import faiss

        load_path = path or self.index_path
        faiss_path = f"{load_path}.faiss"
        docs_path = f"{load_path}.docs.pkl"

        if not os.path.exists(faiss_path) or not os.path.exists(docs_path):
            return False

        self._index = faiss.read_index(faiss_path)

        with open(docs_path, "rb") as f:
            data = pickle.load(f)
            self._documents = [Document(**d) for d in data["documents"]]
            self._id_to_idx = data["id_to_idx"]

        return True


class EmptyRetriever:
    """Fallback retriever that returns empty results."""

    async def search(self, query: str, top_k: int = 5) -> list[dict]:
        return []


def get_retriever() -> FAISSRetriever | EmptyRetriever:
    """Factory function to get the appropriate retriever."""
    retriever = FAISSRetriever()
    if retriever.load():
        return retriever
    return EmptyRetriever()


# Corpus builders for different bot types

POSTMORTEM_CORPUS = [
    {
        "id": "pm-001",
        "text": "We failed because we built something nobody wanted. Market validation came too late.",
        "metadata": {"company": "Flowtab", "failure_cause": "no_market_need", "industry": "food_delivery", "stage": "seed"},
    },
    {
        "id": "pm-002",
        "text": "Running out of cash killed us. We couldn't close our Series A in time.",
        "metadata": {"company": "Homejoy", "failure_cause": "ran_out_of_cash", "industry": "home_services", "stage": "series_a"},
    },
    {
        "id": "pm-003",
        "text": "The founding team couldn't work together. Founder conflict destroyed everything.",
        "metadata": {"company": "Weeby", "failure_cause": "founder_conflict", "industry": "gaming", "stage": "seed"},
    },
    {
        "id": "pm-004",
        "text": "Competition was too fierce. Amazon entered our market and we couldn't compete.",
        "metadata": {"company": "Quidsi", "failure_cause": "competition", "industry": "ecommerce", "stage": "growth"},
    },
    {
        "id": "pm-005",
        "text": "Our pricing model was wrong. We couldn't make unit economics work.",
        "metadata": {"company": "Sidecar", "failure_cause": "pricing_model", "industry": "transportation", "stage": "series_b"},
    },
    {
        "id": "pm-006",
        "text": "The product just wasn't good enough. Users churned immediately.",
        "metadata": {"company": "Color", "failure_cause": "poor_product", "industry": "social", "stage": "series_a"},
    },
    {
        "id": "pm-007",
        "text": "Bad timing. We were too early for the market, before mobile was ready.",
        "metadata": {"company": "Webvan", "failure_cause": "bad_timing", "industry": "grocery_delivery", "stage": "growth"},
    },
    {
        "id": "pm-008",
        "text": "Our pivot failed. We tried to shift business models but ran out of runway.",
        "metadata": {"company": "Turntable.fm", "failure_cause": "pivot_failure", "industry": "music", "stage": "series_a"},
    },
    {
        "id": "pm-009",
        "text": "Regulatory issues killed us. Compliance costs were too high for our stage.",
        "metadata": {"company": "Lumosity", "failure_cause": "legal_regulatory", "industry": "health", "stage": "growth"},
    },
    {
        "id": "pm-010",
        "text": "Founder burnout. After 4 years of grinding, we had nothing left.",
        "metadata": {"company": "Zenefits", "failure_cause": "burnout", "industry": "hr_tech", "stage": "series_b"},
    },
]


def build_postmortem_index() -> FAISSRetriever:
    """Build a FAISS index from the postmortem corpus."""
    retriever = FAISSRetriever()
    documents = [Document(**doc) for doc in POSTMORTEM_CORPUS]
    retriever.add_documents(documents)
    retriever.save()
    return retriever

