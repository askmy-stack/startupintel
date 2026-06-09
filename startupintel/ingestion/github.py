"""GitHub API connector for repository and contributor data."""

from __future__ import annotations

import httpx
from datetime import datetime, timedelta

from startupintel.config import get_settings
from startupintel.ingestion.base import BaseConnector


class GitHubConnector(BaseConnector):
    """Connector for GitHub API to fetch stars, commits, and contributor data."""

    source_name = "github"
    base_url = "https://api.github.com"

    def __init__(self, token: str | None = None):
        self.token = token or get_settings().github_token
        self.headers = {"Accept": "application/vnd.github.v3+json"}
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"

    async def fetch(self, owner: str, repo: str) -> dict:
        """Fetch repository data from GitHub."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get repo details
            repo_data = await self._get_repo(client, owner, repo)

            if not repo_data or "id" not in repo_data:
                return {"found": False, "source": self.source_name}

            # Get additional metrics
            contributors = await self._get_contributors(client, owner, repo)
            commits = await self._get_recent_commits(client, owner, repo)
            languages = await self._get_languages(client, owner, repo)

            return {
                "found": True,
                "source": self.source_name,
                "repo_id": repo_data.get("id"),
                "name": repo_data.get("name"),
                "full_name": repo_data.get("full_name"),
                "stars": repo_data.get("stargazers_count", 0),
                "forks": repo_data.get("forks_count", 0),
                "watchers": repo_data.get("watchers_count", 0),
                "open_issues": repo_data.get("open_issues_count", 0),
                "created_at": repo_data.get("created_at"),
                "updated_at": repo_data.get("updated_at"),
                "pushed_at": repo_data.get("pushed_at"),
                "language": repo_data.get("language"),
                "languages": languages,
                "license": repo_data.get("license", {}).get("spdx_id") if repo_data.get("license") else None,
                "contributors_count": len(contributors),
                "top_contributors": [
                    {
                        "login": c.get("login"),
                        "contributions": c.get("contributions"),
                    }
                    for c in contributors[:10]
                ],
                "recent_commits": [
                    {
                        "sha": c.get("sha")[:7],
                        "message": c.get("commit", {}).get("message", "")[:100],
                        "date": c.get("commit", {}).get("committer", {}).get("date"),
                        "author": c.get("commit", {}).get("author", {}).get("name"),
                    }
                    for c in commits[:20]
                ],
                "description": repo_data.get("description"),
                "homepage": repo_data.get("homepage"),
                "topics": repo_data.get("topics", []),
            }

    async def _get_repo(self, client: httpx.AsyncClient, owner: str, repo: str) -> dict:
        """Get repository details."""
        try:
            response = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}",
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            return {"error": str(e)}

    async def _get_contributors(self, client: httpx.AsyncClient, owner: str, repo: str) -> list[dict]:
        """Get repository contributors."""
        try:
            response = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}/contributors",
                headers=self.headers,
                params={"per_page": 100},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError:
            return []

    async def _get_recent_commits(self, client: httpx.AsyncClient, owner: str, repo: str) -> list[dict]:
        """Get recent commits."""
        since = (datetime.utcnow() - timedelta(days=30)).isoformat()

        try:
            response = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}/commits",
                headers=self.headers,
                params={"since": since, "per_page": 100},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError:
            return []

    async def _get_languages(self, client: httpx.AsyncClient, owner: str, repo: str) -> dict:
        """Get repository languages."""
        try:
            response = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}/languages",
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError:
            return {}

    async def search_repos(self, query: str, sort: str = "stars", per_page: int = 10) -> list[dict]:
        """Search for repositories."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/search/repositories",
                    headers=self.headers,
                    params={"q": query, "sort": sort, "per_page": per_page},
                )
                response.raise_for_status()
                items = response.json().get("items", [])
                return [
                    {
                        "full_name": item.get("full_name"),
                        "stars": item.get("stargazers_count"),
                        "language": item.get("language"),
                        "description": item.get("description"),
                    }
                    for item in items
                ]
            except httpx.HTTPError:
                return []

    async def get_user_repos(self, username: str) -> list[dict]:
        """Get repositories for a user."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/users/{username}/repos",
                    headers=self.headers,
                    params={"sort": "updated", "per_page": 100},
                )
                response.raise_for_status()
                repos = response.json()
                return [
                    {
                        "name": r.get("name"),
                        "stars": r.get("stargazers_count"),
                        "forks": r.get("forks_count"),
                        "language": r.get("language"),
                    }
                    for r in repos
                ]
            except httpx.HTTPError:
                return []

    async def get_repo_activity(self, owner: str, repo: str, days: int = 30) -> dict:
        """Get repository activity metrics."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            commits = await self._get_recent_commits(client, owner, repo)

            # Calculate activity metrics
            commit_dates = [c.get("commit", {}).get("committer", {}).get("date") for c in commits]
            commit_dates = [datetime.fromisoformat(d.replace("Z", "+00:00")) for d in commit_dates if d]

            if not commit_dates:
                return {"commits_30d": 0, "active_days": 0, "avg_commits_per_day": 0}

            active_days = len(set(d.date() for d in commit_dates))

            return {
                "commits_30d": len(commits),
                "active_days": active_days,
                "avg_commits_per_day": round(len(commits) / days, 2),
                "last_commit_date": max(commit_dates).isoformat() if commit_dates else None,
            }
