"""ProductHunt API connector for launch history and upvotes."""

from __future__ import annotations

import httpx
from datetime import datetime

from startupintel.config import get_settings
from startupintel.ingestion.base import BaseConnector


class ProductHuntConnector(BaseConnector):
    """Connector for ProductHunt API to fetch launch history and traction."""

    source_name = "producthunt"
    base_url = "https://api.producthunt.com/v2/api/graphql"

    def __init__(self, token: str | None = None):
        self.token = token or get_settings().producthunt_token
        if not self.token:
            raise ValueError("ProductHunt token required")
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    async def fetch(self, company_name: str) -> dict:
        """Fetch product data from ProductHunt."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Search for posts by company name
            query = """
            query SearchPosts($query: String!) {
                posts(search: $query, first: 10) {
                    edges {
                        node {
                            id
                            name
                            tagline
                            description
                            votesCount
                            commentsCount
                            createdAt
                            url
                            website
                            thumbnail {
                                url
                            }
                            topics {
                                edges {
                                    node {
                                        name
                                    }
                                }
                            }
                            makers {
                                id
                                name
                                username
                                headline
                            }
                        }
                    }
                }
            }
            """

            try:
                response = await client.post(
                    self.base_url,
                    headers=self.headers,
                    json={"query": query, "variables": {"query": company_name}},
                )
                response.raise_for_status()
                data = response.json()

                posts = data.get("data", {}).get("posts", {}).get("edges", [])

                if not posts:
                    return {"found": False, "source": self.source_name}

                # Process posts
                processed_posts = []
                for edge in posts:
                    node = edge.get("node", {})
                    processed_posts.append({
                        "id": node.get("id"),
                        "name": node.get("name"),
                        "tagline": node.get("tagline"),
                        "description": node.get("description"),
                        "votes": node.get("votesCount", 0),
                        "comments": node.get("commentsCount", 0),
                        "created_at": node.get("createdAt"),
                        "url": node.get("url"),
                        "website": node.get("website"),
                        "topics": [t.get("node", {}).get("name") for t in node.get("topics", {}).get("edges", [])],
                        "makers": [
                            {
                                "name": m.get("name"),
                                "username": m.get("username"),
                                "headline": m.get("headline"),
                            }
                            for m in node.get("makers", [])
                        ],
                    })

                # Calculate aggregate metrics
                total_votes = sum(p.get("votes", 0) for p in processed_posts)
                total_comments = sum(p.get("comments", 0) for p in processed_posts)

                return {
                    "found": True,
                    "source": self.source_name,
                    "posts": processed_posts,
                    "total_posts": len(processed_posts),
                    "total_votes": total_votes,
                    "total_comments": total_comments,
                    "avg_votes_per_post": round(total_votes / len(processed_posts), 2) if processed_posts else 0,
                    "first_launch_date": processed_posts[-1].get("created_at") if processed_posts else None,
                    "latest_launch_date": processed_posts[0].get("created_at") if processed_posts else None,
                }

            except httpx.HTTPError as e:
                return {"found": False, "source": self.source_name, "error": str(e)}

    async def fetch_daily_leaderboard(self, date: str | None = None) -> list[dict]:
        """Fetch daily leaderboard for a specific date."""
        target_date = date or datetime.utcnow().strftime("%Y-%m-%d")

        async with httpx.AsyncClient(timeout=30.0) as client:
            query = """
            query DailyLeaderboard($date: Date!) {
                posts(order: RANKING, postedAfter: $date, postedBefore: $date, first: 20) {
                    edges {
                        node {
                            id
                            name
                            votesCount
                            commentsCount
                            ranking
                        }
                    }
                }
            }
            """

            try:
                response = await client.post(
                    self.base_url,
                    headers=self.headers,
                    json={"query": query, "variables": {"date": target_date}},
                )
                response.raise_for_status()
                data = response.json()

                posts = data.get("data", {}).get("posts", {}).get("edges", [])

                return [
                    {
                        "id": p.get("node", {}).get("id"),
                        "name": p.get("node", {}).get("name"),
                        "votes": p.get("node", {}).get("votesCount", 0),
                        "comments": p.get("node", {}).get("commentsCount", 0),
                        "ranking": p.get("node", {}).get("ranking"),
                    }
                    for p in posts
                ]

            except httpx.HTTPError:
                return []

    async def fetch_user_products(self, username: str) -> list[dict]:
        """Fetch all products by a user."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            query = """
            query UserProducts($username: String!) {
                user(username: $username) {
                    madePosts(first: 20) {
                        edges {
                            node {
                                id
                                name
                                votesCount
                                createdAt
                            }
                        }
                    }
                }
            }
            """

            try:
                response = await client.post(
                    self.base_url,
                    headers=self.headers,
                    json={"query": query, "variables": {"username": username}},
                )
                response.raise_for_status()
                data = response.json()

                posts = data.get("data", {}).get("user", {}).get("madePosts", {}).get("edges", [])

                return [
                    {
                        "id": p.get("node", {}).get("id"),
                        "name": p.get("node", {}).get("name"),
                        "votes": p.get("node", {}).get("votesCount", 0),
                        "created_at": p.get("node", {}).get("createdAt"),
                    }
                    for p in posts
                ]

            except httpx.HTTPError:
                return []
