import re

import httpx

from app.config import settings

REPO_PATTERN = re.compile(r"^[\w.-]+/[\w.-]+$")

GITHUB_API_URL = "https://api.github.com"


class GithubRepoNotFound(Exception):
    pass


class GithubApiError(Exception):
    pass


def _headers() -> dict[str, str]:
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"
    return headers


def is_valid_repo_format(repo: str) -> bool:
    return bool(REPO_PATTERN.match(repo))


async def verify_repo(repo: str) -> None:
    """Raises GithubRepoNotFound or GithubApiError; returns silently if the repo is reachable."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(f"{GITHUB_API_URL}/repos/{repo}", headers=_headers())
        except httpx.HTTPError as exc:
            raise GithubApiError(str(exc)) from exc

    if response.status_code == 404:
        raise GithubRepoNotFound(repo)
    if response.status_code != 200:
        raise GithubApiError(f"GitHub a répondu {response.status_code}")


async def list_issues(repo: str) -> list[dict]:
    """Returns raw GitHub issue payloads for all states (pull requests excluded), paginated to completion."""
    issues: list[dict] = []
    url = f"{GITHUB_API_URL}/repos/{repo}/issues"
    params = {"state": "all", "per_page": 100}

    async with httpx.AsyncClient(timeout=15.0) as client:
        while url:
            try:
                response = await client.get(url, headers=_headers(), params=params)
            except httpx.HTTPError as exc:
                raise GithubApiError(str(exc)) from exc

            if response.status_code == 404:
                raise GithubRepoNotFound(repo)
            if response.status_code != 200:
                raise GithubApiError(f"GitHub a répondu {response.status_code}")

            issues.extend(item for item in response.json() if "pull_request" not in item)

            url = response.links.get("next", {}).get("url")
            params = None  # already encoded in the "next" URL

    return issues
