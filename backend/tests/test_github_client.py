import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app import github_client


def _http_response(status_code: int, json_body: dict) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_body
    return response


def _issue_node(
    number: int,
    *,
    title: str = "Titre",
    state: str = "OPEN",
    labels: list[str] | None = None,
    closed_at: str | None = None,
    story_points: float | None = None,
) -> dict:
    field_value = {"number": story_points} if story_points is not None else None
    return {
        "number": number,
        "title": title,
        "state": state,
        "url": f"https://github.com/owner/repo/issues/{number}",
        "closedAt": closed_at,
        "labels": {"nodes": [{"name": label} for label in (labels or [])]},
        "projectItems": {"nodes": [{"fieldValueByName": field_value}]},
    }


def _page(nodes: list[dict], *, has_next_page: bool = False, end_cursor: str | None = None) -> dict:
    return {
        "data": {
            "repository": {
                "issues": {
                    "pageInfo": {"hasNextPage": has_next_page, "endCursor": end_cursor},
                    "nodes": nodes,
                }
            }
        }
    }


def test_list_issues_parses_labels_story_points_and_closed_at():
    body = _page(
        [
            _issue_node(1, title="US ouverte", state="OPEN", labels=["Sprint 1"], story_points=3),
            _issue_node(
                2,
                title="US fermée",
                state="CLOSED",
                labels=["Sprint 1"],
                closed_at="2026-08-10T12:00:00Z",
                story_points=5,
            ),
        ]
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = _http_response(200, body)
        issues = asyncio.run(github_client.list_issues("owner/repo"))

    assert len(issues) == 2
    assert issues[0] == {
        "number": 1,
        "title": "US ouverte",
        "state": "open",
        "html_url": "https://github.com/owner/repo/issues/1",
        "labels": [{"name": "Sprint 1"}],
        "closed_at": None,
        "story_points": 3,
    }
    assert issues[1]["state"] == "closed"
    assert issues[1]["closed_at"] == "2026-08-10T12:00:00Z"
    assert issues[1]["story_points"] == 5


def test_list_issues_treats_missing_project_field_as_no_story_points():
    body = _page([_issue_node(1, labels=[], story_points=None)])

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = _http_response(200, body)
        issues = asyncio.run(github_client.list_issues("owner/repo"))

    assert issues[0]["story_points"] is None


def test_list_issues_tolerates_projectitems_denied_by_scope():
    # A token without `read:project` makes GitHub return `projectItems: null` for
    # that node (with a partial GraphQL error) rather than failing the request.
    node = _issue_node(1, labels=["Sprint 1"])
    node["projectItems"] = None
    body = _page([node])
    body["errors"] = [{"message": "Resource not accessible by integration"}]

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = _http_response(200, body)
        issues = asyncio.run(github_client.list_issues("owner/repo"))

    assert issues[0]["story_points"] is None


def test_list_issues_follows_pagination():
    first_page = _page([_issue_node(1)], has_next_page=True, end_cursor="cursor-1")
    second_page = _page([_issue_node(2)], has_next_page=False)

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = [_http_response(200, first_page), _http_response(200, second_page)]
        issues = asyncio.run(github_client.list_issues("owner/repo"))

    assert [issue["number"] for issue in issues] == [1, 2]
    assert mock_post.call_count == 2
    second_call_variables = mock_post.call_args_list[1].kwargs["json"]["variables"]
    assert second_call_variables["cursor"] == "cursor-1"


def test_list_issues_repository_not_found_raises():
    body = {"data": {"repository": None}}

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = _http_response(200, body)
        with pytest.raises(github_client.GithubRepoNotFound):
            asyncio.run(github_client.list_issues("owner/repo"))


def test_list_issues_graphql_error_without_data_raises_api_error():
    body = {"errors": [{"message": "Bad credentials"}]}

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = _http_response(200, body)
        with pytest.raises(github_client.GithubApiError):
            asyncio.run(github_client.list_issues("owner/repo"))


def test_list_issues_non_200_raises_api_error():
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = _http_response(502, {})
        with pytest.raises(github_client.GithubApiError):
            asyncio.run(github_client.list_issues("owner/repo"))
