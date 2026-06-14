"""Tests for the Elasticsearch wrapper (lazy dep; fake client injected)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from startupintel.utils.elasticsearch import ElasticsearchClient, get_es_client

pytestmark = pytest.mark.asyncio


class FakeIndices:
    def __init__(self):
        self.created: list[str] = []
        self._exists = False

    async def exists(self, index):
        return self._exists

    async def create(self, index, body=None):
        self.created.append(index)
        self._exists = True


class FakeES:
    def __init__(self):
        self.indices = FakeIndices()
        self.indexed: list[dict] = []
        self.deleted: list[str] = []
        self.closed = False
        self.search_response: dict = {"hits": {"hits": [], "total": {"value": 0}}}

    async def index(self, index, id, document):
        self.indexed.append({"index": index, "id": id, "document": document})
        return {"result": "created"}

    async def search(self, index, body):
        return self.search_response

    async def delete(self, index, id):
        self.deleted.append(id)

    async def close(self):
        self.closed = True


def _client_with_fake() -> tuple[ElasticsearchClient, FakeES]:
    client = ElasticsearchClient()
    fake = FakeES()
    client.client = fake
    return client, fake


async def test_unconfigured_methods_short_circuit():
    client = ElasticsearchClient()
    client.client = None
    assert "error" in await client.index_startup(uuid4(), "n", "d", None, None)
    search = await client.search_startups("q")
    assert search["items"] == [] and search["total"] == 0
    assert await client.autocomplete("name", "ab") == []
    assert "error" in await client.delete_startup(uuid4())
    # ensure_index / connect are no-ops without a client/url.
    await client.ensure_index("startups")


async def test_connect_skips_without_url(monkeypatch):
    client = ElasticsearchClient()
    monkeypatch.setattr(client.settings, "elasticsearch_url", None)
    await client.connect()
    assert client.client is None


async def test_index_startup_creates_index_and_document():
    client, fake = _client_with_fake()
    sid = uuid4()
    result = await client.index_startup(sid, "Acme", "acme.io", "saas", "seed")
    assert result["success"] is True
    assert fake.indexed[0]["id"] == str(sid)
    assert "startupintel_startups" in fake.indices.created


async def test_search_parses_hits_and_paginates():
    client, fake = _client_with_fake()
    fake.search_response = {
        "hits": {
            "total": {"value": 1},
            "hits": [
                {
                    "_id": "x",
                    "_score": 2.5,
                    "_source": {
                        "id": "abc",
                        "name": "Acme",
                        "domain": "acme.io",
                        "industry": "saas",
                        "stage": "seed",
                        "description": "d",
                    },
                    "highlight": {"name": ["<em>Acme</em>"]},
                }
            ],
        }
    }
    result = await client.search_startups("acme", filters={"stage": "seed"}, page=1, page_size=20)
    assert result["total"] == 1
    assert result["total_pages"] == 1
    assert result["items"][0]["name"] == "Acme"
    assert result["items"][0]["score"] == 2.5


async def test_autocomplete_and_delete():
    client, fake = _client_with_fake()
    fake.search_response = {
        "suggest": {"suggestions": [{"options": [{"text": "Acme"}, {"text": "Acorn"}]}]}
    }
    assert await client.autocomplete("name", "Ac") == ["Acme", "Acorn"]

    sid = uuid4()
    assert (await client.delete_startup(sid)) == {"success": True}
    assert str(sid) in fake.deleted


async def test_close_and_singleton_accessor():
    client, fake = _client_with_fake()
    await client.close()
    assert fake.closed is True
    assert isinstance(await get_es_client(), ElasticsearchClient)
