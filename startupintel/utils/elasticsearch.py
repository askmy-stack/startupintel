"""Elasticsearch integration for advanced search."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from elasticsearch import AsyncElasticsearch

from startupintel.config import get_settings


class ElasticsearchClient:
    """Elasticsearch client wrapper."""
    
    def __init__(self):
        self.settings = get_settings()
        self.client: AsyncElasticsearch | None = None
        self.index_prefix = "startupintel"
    
    async def connect(self) -> None:
        """Initialize Elasticsearch connection."""
        if not self.settings.elasticsearch_url:
            return
        
        self.client = AsyncElasticsearch([self.settings.elasticsearch_url])
    
    async def close(self) -> None:
        """Close Elasticsearch connection."""
        if self.client:
            await self.client.close()
    
    async def ensure_index(self, index_name: str, mappings: dict | None = None) -> None:
        """Ensure index exists with proper mappings."""
        if not self.client:
            return
        
        full_index_name = f"{self.index_prefix}_{index_name}"
        
        exists = await self.client.indices.exists(index=full_index_name)
        if not exists:
            body = {"mappings": mappings} if mappings else {}
            await self.client.indices.create(index=full_index_name, body=body)
    
    async def index_startup(
        self,
        startup_id: UUID,
        name: str,
        domain: str,
        industry: str | None,
        stage: str | None,
        description: str | None = None,
        metadata: dict | None = None,
    ) -> dict:
        """Index a startup document."""
        if not self.client:
            return {"error": "Elasticsearch not configured"}
        
        await self.ensure_index("startups", {
            "properties": {
                "name": {"type": "text", "analyzer": "standard"},
                "domain": {"type": "keyword"},
                "industry": {"type": "keyword"},
                "stage": {"type": "keyword"},
                "description": {"type": "text", "analyzer": "standard"},
                "created_at": {"type": "date"},
            }
        })
        
        doc = {
            "id": str(startup_id),
            "name": name,
            "domain": domain,
            "industry": industry,
            "stage": stage,
            "description": description,
            "metadata": metadata or {},
            "created_at": datetime.now(UTC).isoformat(),
        }
        
        response = await self.client.index(
            index=f"{self.index_prefix}_startups",
            id=str(startup_id),
            document=doc,
        )
        
        return {"success": True, "result": response["result"]}
    
    async def search_startups(
        self,
        query: str,
        filters: dict | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """Search startups with full-text and filters."""
        if not self.client:
            return {"error": "Elasticsearch not configured", "items": [], "total": 0}
        
        # Build query
        must_clauses = []
        
        if query:
            must_clauses.append({
                "multi_match": {
                    "query": query,
                    "fields": ["name^3", "domain^2", "description", "industry"],
                    "type": "best_fields",
                    "fuzziness": "AUTO",
                }
            })
        
        # Add filters
        filter_clauses = []
        if filters:
            if "industry" in filters:
                filter_clauses.append({"term": {"industry": filters["industry"]}})
            if "stage" in filters:
                filter_clauses.append({"term": {"stage": filters["stage"]}})
            if "created_after" in filters:
                filter_clauses.append({"range": {"created_at": {"gte": filters["created_after"]}}})
        
        search_body = {
            "query": {
                "bool": {
                    "must": must_clauses,
                    "filter": filter_clauses,
                }
            },
            "highlight": {
                "fields": {
                    "name": {},
                    "description": {},
                }
            },
            "from": (page - 1) * page_size,
            "size": page_size,
            "sort": [{"_score": "desc"}],
        }
        
        if not query:
            # Match all if no query
            search_body["query"]["bool"]["must"] = [{"match_all": {}}]
        
        response = await self.client.search(
            index=f"{self.index_prefix}_startups",
            body=search_body,
        )
        
        hits = response["hits"]["hits"]
        total = response["hits"]["total"]["value"]
        
        items = []
        for hit in hits:
            item = {
                "id": hit["_source"]["id"],
                "name": hit["_source"]["name"],
                "domain": hit["_source"]["domain"],
                "industry": hit["_source"].get("industry"),
                "stage": hit["_source"].get("stage"),
                "description": hit["_source"].get("description"),
                "score": hit["_score"],
                "highlights": hit.get("highlight", {}),
            }
            items.append(item)
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if total > 0 else 1,
        }
    
    async def autocomplete(
        self,
        field: str,
        prefix: str,
        size: int = 10,
    ) -> list[str]:
        """Autocomplete suggestions."""
        if not self.client:
            return []
        
        response = await self.client.search(
            index=f"{self.index_prefix}_startups",
            body={
                "suggest": {
                    "suggestions": {
                        "prefix": prefix,
                        "completion": {
                            "field": f"{field}_suggest",
                            "size": size,
                        }
                    }
                }
            }
        )
        
        suggestions = response["suggest"]["suggestions"][0]["options"]
        return [s["text"] for s in suggestions]
    
    async def delete_startup(self, startup_id: UUID) -> dict:
        """Remove startup from index."""
        if not self.client:
            return {"error": "Elasticsearch not configured"}
        
        try:
            await self.client.delete(
                index=f"{self.index_prefix}_startups",
                id=str(startup_id),
            )
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}


# Global ES client instance
es_client = ElasticsearchClient()


async def get_es_client() -> ElasticsearchClient:
    """Get Elasticsearch client (for dependency injection)."""
    return es_client
