class EmptyRetriever:
    async def search(self, query: str, top_k: int = 5) -> list[dict]:
        return []

