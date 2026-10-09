import re

import httpx

from app.config import settings

# Règles de nommage GitHub : propriétaire en ASCII alphanumérique et tirets
# (39 caractères max, pas de tiret initial), dépôt en ASCII alphanumérique,
# points, tirets et soulignés (100 max). "." et ".." sont exclus : interpolés
# dans l'URL REST (/repos/{owner}/{repo}), ils feraient sortir de /repos et
# appeler d'autres routes de l'API GitHub avec le token du serveur.
OWNER_PATTERN = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})")
REPO_NAME_PATTERN = re.compile(r"[A-Za-z0-9._-]{1,100}")

GITHUB_API_URL = "https://api.github.com"
GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"

# Plafond d'une synchronisation : 40 pages de 50 issues. Sans limite, lier un
# dépôt public géant (des centaines de milliers d'issues) déclencherait des
# milliers d'appels GraphQL à chaque synchro et épuiserait le quota horaire du
# token du serveur, partagé par tous les projets.
MAX_ISSUE_PAGES = 40
ISSUES_PER_PAGE = 50
MAX_ISSUES = MAX_ISSUE_PAGES * ISSUES_PER_PAGE

# Nom du champ personnalisé de GitHub Projects (v2) utilisé par l'équipe pour
# valoriser une US en story points (voir US-29 — burndown chart).
STORY_POINTS_FIELD_NAME = "Valorisation"

# Bloc demandé en plus des champs de base pour récupérer la valorisation et
# l'itération (champ "Iteration" de GitHub Projects, que l'équipe renomme en
# "Sprint 0", "Sprint 1"... et qui rattache l'US à un sprint, au même titre
# qu'un label du même nom).
# `Issue.projectItems` est non-nullable dans le schéma GraphQL de GitHub : si le
# token ne peut pas lire le Project (Project privé, token fine-grained face à un
# Project appartenant à un compte utilisateur...), l'erreur remonte jusqu'à
# l'issue entière, qui revient à `null` dans `nodes`.
_PROJECT_ITEMS_FIELDS = """
        projectItems(first: 10) {
          nodes {
            fieldValueByName(name: "%s") {
              ... on ProjectV2ItemFieldNumberValue { number }
            }
            fieldValues(first: 20) {
              nodes {
                ... on ProjectV2ItemFieldIterationValue { title }
              }
            }
          }
        }""" % STORY_POINTS_FIELD_NAME

_ISSUES_QUERY_TEMPLATE = """
query($owner: String!, $name: String!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    issues(first: %d, after: $cursor, states: [OPEN, CLOSED]) {
      pageInfo { hasNextPage endCursor }
      nodes {
        number
        title
        state
        url
        closedAt
        labels(first: 30) { nodes { name } }%s
      }
    }
  }
}
"""

_ISSUES_QUERY = _ISSUES_QUERY_TEMPLATE % (ISSUES_PER_PAGE, _PROJECT_ITEMS_FIELDS)
_ISSUES_QUERY_WITHOUT_STORY_POINTS = _ISSUES_QUERY_TEMPLATE % (ISSUES_PER_PAGE, "")


class GithubRepoNotFound(Exception):
    pass


class GithubApiError(Exception):
    pass


class GithubProjectsUnavailable(GithubApiError):
    """GitHub a refusé l'accès aux Projects (v2) liés aux issues : la valorisation
    ne peut pas être lue avec ce token, mais les issues elles-mêmes restent
    récupérables sans elle."""


def _headers() -> dict[str, str]:
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"
    return headers


def is_valid_repo_format(repo: str) -> bool:
    owner, separator, name = repo.partition("/")
    return bool(
        separator
        and OWNER_PATTERN.fullmatch(owner)
        and REPO_NAME_PATTERN.fullmatch(name)
        and name not in (".", "..")
    )


async def verify_repo(repo: str) -> bool:
    """Raises GithubRepoNotFound or GithubApiError; returns whether the reachable repo is private."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(f"{GITHUB_API_URL}/repos/{repo}", headers=_headers())
        except httpx.HTTPError as exc:
            raise GithubApiError(str(exc)) from exc

    if response.status_code == 404:
        raise GithubRepoNotFound(repo)
    if response.status_code != 200:
        raise GithubApiError(f"GitHub a répondu {response.status_code}")
    return bool(response.json().get("private"))


def _story_points_from_node(node: dict) -> float | None:
    project_items = node.get("projectItems") or {}
    for item in project_items.get("nodes") or []:
        field_value = (item or {}).get("fieldValueByName")
        if field_value and "number" in field_value:
            return field_value["number"]
    return None


def _iteration_from_node(node: dict) -> str | None:
    project_items = node.get("projectItems") or {}
    for item in project_items.get("nodes") or []:
        field_values = (item or {}).get("fieldValues") or {}
        for value in field_values.get("nodes") or []:
            if value and value.get("title"):
                return value["title"]
    return None


def _parse_issue_node(node: dict) -> dict:
    return {
        "number": node["number"],
        "title": node["title"],
        "state": node["state"].lower(),
        "html_url": node["url"],
        "labels": [{"name": label["name"]} for label in node["labels"]["nodes"] if label],
        "closed_at": node.get("closedAt"),
        "story_points": _story_points_from_node(node),
        "iteration": _iteration_from_node(node),
    }


def _first_error_message(body: dict) -> str:
    errors = body.get("errors") or []
    if errors and isinstance(errors[0], dict) and errors[0].get("message"):
        return str(errors[0]["message"])
    return "Réponse GraphQL invalide."


async def list_issues(repo: str, *, with_story_points: bool = True) -> list[dict]:
    """Returns raw GitHub issue payloads for all states (pull requests excluded), paginated to completion.

    Uses the GraphQL API (rather than REST) so that each issue's "Valorisation"
    GitHub Projects (v2) custom field — used as its story-point value for the
    burndown chart — and its closedAt timestamp come back in the same request
    as its labels, without extra round-trips.

    Raises GithubProjectsUnavailable when GitHub nulls issues because the token
    cannot read their Project; `with_story_points=False` skips that field so the
    issues can still be fetched (with `story_points` set to None).
    """
    owner, name = repo.split("/", 1)
    query = _ISSUES_QUERY if with_story_points else _ISSUES_QUERY_WITHOUT_STORY_POINTS
    issues: list[dict] = []
    cursor: str | None = None

    async with httpx.AsyncClient(timeout=15.0) as client:
        for _page in range(MAX_ISSUE_PAGES):
            variables = {"owner": owner, "name": name, "cursor": cursor}
            try:
                response = await client.post(
                    GITHUB_GRAPHQL_URL, headers=_headers(), json={"query": query, "variables": variables}
                )
            except httpx.HTTPError as exc:
                raise GithubApiError(str(exc)) from exc

            if response.status_code != 200:
                raise GithubApiError(f"GitHub a répondu {response.status_code}")

            body = response.json()
            data = body.get("data")
            repository = data.get("repository") if data else None
            if repository is None:
                if data is None:
                    raise GithubApiError(_first_error_message(body))
                raise GithubRepoNotFound(repo)

            issues_page = repository["issues"]
            nodes = issues_page["nodes"] or []
            if any(node is None for node in nodes):
                message = _first_error_message(body)
                if with_story_points:
                    raise GithubProjectsUnavailable(message)
                raise GithubApiError(message)
            issues.extend(_parse_issue_node(node) for node in nodes)

            page_info = issues_page["pageInfo"]
            if not page_info["hasNextPage"]:
                break
            cursor = page_info["endCursor"]

    return issues
