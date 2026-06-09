"""Twitter/X API connector for founder sentiment and mentions."""

from __future__ import annotations

import httpx
from datetime import datetime, timedelta

from startupintel.config import get_settings
from startupintel.ingestion.base import BaseConnector


class TwitterConnector(BaseConnector):
    """Connector for Twitter/X API to fetch founder sentiment and mention data."""

    source_name = "twitter"
    base_url = "https://api.twitter.com/2"

    def __init__(self, bearer_token: str | None = None):
        self.bearer_token = bearer_token or get_settings().twitter_bearer_token
        if not self.bearer_token:
            raise ValueError("Twitter bearer token required")
        self.headers = {"Authorization": f"Bearer {self.bearer_token}"}

    async def fetch(self, username: str) -> dict:
        """Fetch user data and recent tweets."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get user ID
            user_data = await self._get_user(client, username)
            if not user_data or "data" not in user_data:
                return {"found": False, "source": self.source_name}

            user_id = user_data["data"]["id"]

            # Get recent tweets
            tweets = await self._get_user_tweets(client, user_id)

            # Analyze sentiment
            sentiment = self._analyze_sentiment(tweets)

            return {
                "found": True,
                "source": self.source_name,
                "user_id": user_id,
                "username": username,
                "display_name": user_data["data"].get("name"),
                "followers_count": user_data["data"].get("public_metrics", {}).get("followers_count", 0),
                "following_count": user_data["data"].get("public_metrics", {}).get("following_count", 0),
                "tweet_count": user_data["data"].get("public_metrics", {}).get("tweet_count", 0),
                "verified": user_data["data"].get("verified", False),
                "recent_tweets": [
                    {
                        "id": t.get("id"),
                        "text": t.get("text"),
                        "created_at": t.get("created_at"),
                        "likes": t.get("public_metrics", {}).get("like_count", 0),
                        "retweets": t.get("public_metrics", {}).get("retweet_count", 0),
                        "replies": t.get("public_metrics", {}).get("reply_count", 0),
                    }
                    for t in tweets.get("data", [])
                ],
                "sentiment_analysis": sentiment,
            }

    async def _get_user(self, client: httpx.AsyncClient, username: str) -> dict:
        """Get user by username."""
        try:
            response = await client.get(
                f"{self.base_url}/users/by/username/{username}",
                headers=self.headers,
                params={"user.fields": "public_metrics,verified,created_at"},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            return {"error": str(e)}

    async def _get_user_tweets(self, client: httpx.AsyncClient, user_id: str) -> dict:
        """Get recent tweets for a user."""
        try:
            response = await client.get(
                f"{self.base_url}/users/{user_id}/tweets",
                headers=self.headers,
                params={
                    "max_results": 50,
                    "tweet.fields": "created_at,public_metrics,context_annotations",
                },
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError:
            return {"data": []}

    def _analyze_sentiment(self, tweets: dict) -> dict:
        """Simple sentiment analysis of tweets."""
        from textblob import TextBlob

        texts = [t.get("text", "") for t in tweets.get("data", [])]

        if not texts:
            return {"score": 0.0, "mood": "neutral"}

        sentiments = []
        for text in texts:
            blob = TextBlob(text)
            sentiments.append(blob.sentiment.polarity)

        avg_sentiment = sum(sentiments) / len(sentiments)

        mood = "neutral"
        if avg_sentiment > 0.2:
            mood = "positive"
        elif avg_sentiment < -0.2:
            mood = "negative"

        return {
            "score": round(avg_sentiment, 3),
            "mood": mood,
            "tweet_count_analyzed": len(texts),
        }

    async def search_mentions(self, query: str, days: int = 7) -> dict:
        """Search for mentions of a company or topic."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # Calculate date range
                end_time = datetime.utcnow()
                start_time = end_time - timedelta(days=days)

                response = await client.get(
                    f"{self.base_url}/tweets/search/recent",
                    headers=self.headers,
                    params={
                        "query": query,
                        "max_results": 100,
                        "start_time": start_time.isoformat() + "Z",
                        "end_time": end_time.isoformat() + "Z",
                        "tweet.fields": "created_at,public_metrics,author_id",
                    },
                )
                response.raise_for_status()
                data = response.json()

                tweets = data.get("data", [])

                return {
                    "query": query,
                    "total_results": len(tweets),
                    "results": [
                        {
                            "id": t.get("id"),
                            "text": t.get("text"),
                            "created_at": t.get("created_at"),
                            "likes": t.get("public_metrics", {}).get("like_count", 0),
                            "retweets": t.get("public_metrics", {}).get("retweet_count", 0),
                        }
                        for t in tweets
                    ],
                }
            except httpx.HTTPError as e:
                return {"error": str(e), "total_results": 0}

    async def get_founder_activity(self, username: str, days: int = 7) -> dict:
        """Get founder activity metrics."""
        data = await self.fetch(username)

        if not data.get("found"):
            return {"found": False}

        recent_tweets = data.get("recent_tweets", [])

        # Filter to last N days
        cutoff = datetime.utcnow() - timedelta(days=days)
        recent = [
            t for t in recent_tweets
            if datetime.fromisoformat(t["created_at"].replace("Z", "+00:00")).replace(tzinfo=None) > cutoff
        ]

        # Calculate engagement
        total_likes = sum(t.get("likes", 0) for t in recent)
        total_retweets = sum(t.get("retweets", 0) for t in recent)

        return {
            "found": True,
            "username": username,
            "days_analyzed": days,
            "tweet_count": len(recent),
            "total_likes": total_likes,
            "total_retweets": total_retweets,
            "avg_likes_per_tweet": round(total_likes / len(recent), 2) if recent else 0,
            "sentiment": data.get("sentiment_analysis", {}),
        }
