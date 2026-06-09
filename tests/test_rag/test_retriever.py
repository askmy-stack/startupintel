"""Tests for the RAG retriever.

These cover the dependency-light paths (Document, EmptyRetriever fallback,
the get_retriever factory, and search guards). The FAISS/sentence-transformers
encode+search path requires the optional ML dependencies and is exercised in a
separate ML-deps slice.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from startupintel.rag.retriever import (
    Document,
    EmptyRetriever,
    FAISSRetriever,
    get_retriever,
)


def test_document_to_dict():
    doc = Document(id="d1", text="hello", metadata={"source": "test"})
    assert doc.to_dict() == {
        "id": "d1",
        "text": "hello",
        "metadata": {"source": "test"},
    }


def test_document_defaults_metadata():
    assert Document(id="d2", text="x").metadata == {}


@pytest.mark.asyncio
async def test_empty_retriever_returns_empty():
    retriever = EmptyRetriever()
    assert await retriever.search("any query") == []
    assert await retriever.search("test", top_k=10) == []


@pytest.mark.asyncio
async def test_faiss_search_without_index_returns_empty():
    """search short-circuits to [] when no index has been built (no ML deps hit)."""
    retriever = FAISSRetriever(index_path="/tmp/does-not-exist")
    assert retriever._index is None
    assert await retriever.search("query") == []


def test_get_retriever_falls_back_when_no_index():
    """With no index on disk, the factory yields the EmptyRetriever fallback."""
    with patch.object(FAISSRetriever, "load", return_value=False):
        assert isinstance(get_retriever(), EmptyRetriever)


def test_get_retriever_returns_faiss_when_index_loads():
    with patch.object(FAISSRetriever, "load", return_value=True):
        assert isinstance(get_retriever(), FAISSRetriever)


def test_faiss_retriever_reads_config_defaults():
    r = FAISSRetriever()
    assert r.top_k == 5
    assert r.similarity_threshold == 0.7
