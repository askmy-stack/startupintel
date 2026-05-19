"""Tests for RAG retriever."""

from __future__ import annotations

import pytest
import numpy as np
from unittest.mock import Mock, patch

from startupintel.rag.retriever import FAISSRetriever, EmptyRetriever, get_retriever


@pytest.fixture
def mock_embeddings():
    """Create mock embeddings."""
    return np.random.rand(10, 384).astype("float32")


@pytest.fixture
def mock_documents():
    """Create mock documents."""
    return [
        {"id": f"doc_{i}", "text": f"Document {i} content", "metadata": {"source": "test"}}
        for i in range(10)
    ]


@pytest.mark.asyncio
async def test_faiss_retriever(mock_embeddings, mock_documents):
    """Test FAISS retriever."""
    with patch("faiss.read_index") as mock_read:
        mock_index = Mock()
        mock_index.search.return_value = (np.array([[0.5, 0.3]]), np.array([[0, 1]]))
        mock_read.return_value = mock_index

        retriever = FAISSRetriever(
            index_path="test.index",
            documents=mock_documents,
            embeddings=mock_embeddings,
        )
        retriever.index = mock_index
        retriever.documents = mock_documents

        results = await retriever.retrieve("test query", top_k=2)

        assert len(results) == 2
        assert results[0]["id"] == "doc_0"
        assert results[0]["score"] == 0.5


@pytest.mark.asyncio
async def test_empty_retriever():
    """Test empty retriever."""
    retriever = EmptyRetriever()

    results = await retriever.retrieve("any query")
    assert results == []

    # Test that it can be used as a fallback
    assert await retriever.retrieve("test") == []


def test_get_retriever_empty():
    """Test getting retriever when index doesn't exist."""
    with patch("os.path.exists") as mock_exists:
        mock_exists.return_value = False

        retriever = get_retriever()
        assert isinstance(retriever, EmptyRetriever)
