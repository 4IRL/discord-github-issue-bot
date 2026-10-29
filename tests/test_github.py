from collections.abc import Callable
from dataclasses import replace
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock

import aiohttp
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from issue_bot.complexity import Complexity
from issue_bot.config import Config, TargetConfig
from issue_bot.github import (
    LABEL_COLOR,
    PROJECT_FIELDS_QUERY,
    SET_TRACK_MUTATION,
    FiledIssue,
    GitHubClient,
    GitHubError,
    ProjectFields,
    Transport,
    app_jwt,
)

TOKEN_URL = "https://api.github.com/app/installations/444/access_tokens"
ISSUE_URL = "https://api.github.com/repos/example-org/example-repo/issues"
LABEL_URL = "https://api.github.com/repos/example-org/example-repo/labels"
GRAPHQL_URL = "https://api.github.com/graphql"
HTML_URL = "https://github.com/example-org/example-repo/issues/7"
EXPIRES_AT = "2026-10-18T13:00:00Z"
EXPIRES_AT_EPOCH = datetime.fromisoformat(EXPIRES_AT).timestamp()


def make_client(
    github_private_key: rsa.RSAPrivateKey,
    transport: Transport,
    clock: Callable[[], float] = lambda: 1_000_000.0,
) -> GitHubClient:
    return GitHubClient(333, 444, github_private_key, transport=transport, clock=clock)


def token_response(expires_at: str = EXPIRES_AT) -> tuple[int, dict[str, Any]]:
    return 201, {"token": "ghs_secret_token", "expires_at": expires_at}


def issue_response() -> tuple[int, dict[str, Any]]:
    return 201, {"number": 7, "html_url": HTML_URL, "node_id": "I_node7"}


async def create(client: GitHubClient, route: TargetConfig) -> FiledIssue:
    return await client.create_issue(route, "Title", "Body", ["bug"])


async def test_create_issue_success(
    github_private_key: rsa.RSAPrivateKey, route: TargetConfig
) -> None:
    transport = AsyncMock(side_effect=[token_response(), issue_response()])
    client = make_client(github_private_key, transport)

    result = await client.create_issue(route, "Title", "Body", ["bug"])

    assert result == FiledIssue(7, HTML_URL, "I_node7")
    assert transport.await_count == 2
    token_call, issue_call = transport.call_args_list
    method, url, token_headers, payload = token_call.args
    assert (method, url) == ("POST", TOKEN_URL)
    assert payload == {"repository_ids": [222], "permissions": {"issues": "write"}}
    scheme, app_token = token_headers["Authorization"].split(" ", 1)
    assert scheme == "Bearer"
    claims = jwt.decode(
        app_token,
        github_private_key.public_key(),
        algorithms=["RS256"],
        options={"verify_exp": False, "verify_iat": False},
    )
    assert claims["iss"] == "333"
    method, url, issue_headers, payload = issue_call.args
    assert (method, url) == ("POST", ISSUE_URL)
    assert payload == {"title": "Title", "body": "Body", "labels": ["bug"]}
    for headers in (token_headers, issue_headers):
        assert headers["Accept"] == "application/vnd.github+json"
        assert headers["X-GitHub-Api-Version"] == "2022-11-28"
        assert headers["User-Agent"] == "discord-github-issue-bot"
    assert issue_headers["Authorization"] == "Bearer ghs_secret_token"


def test_app_jwt_claims(github_private_key: rsa.RSAPrivateKey) -> None:
    now = 1_700_000_000
    token = app_jwt(333, github_private_key, now + 0.75)
    claims = jwt.decode(
        token,
        github_private_key.public_key(),
        algorithms=["RS256"],
        options={"verify_exp": False, "verify_iat": False},
    )
    assert claims["iss"] == "333"
    assert claims["iat"] == now - 60
    assert claims["exp"] == now + 540


async def test_token_reused_until_near_expiry(
    github_private_key: rsa.RSAPrivateKey, route: TargetConfig
) -> None:
    transport = AsyncMock(side_effect=[token_response(), issue_response(), issue_response()])
    client = make_client(github_private_key, transport, clock=lambda: EXPIRES_AT_EPOCH - 301)

    await create(client, route)
    await create(client, route)

    assert transport.await_count == 3
    assert [call.args[1] for call in transport.call_args_list] == [
        TOKEN_URL,
        ISSUE_URL,
        ISSUE_URL,
    ]


async def test_two_routes_mint_separate_tokens(
    github_private_key: rsa.RSAPrivateKey, two_route_config: Config
) -> None:
    first, second = two_route_config.routes.values()
    transport = AsyncMock(
        side_effect=[
            token_response(),
            issue_response(),
            token_response(),
            issue_response(),
            issue_response(),
        ]
    )
    client = make_client(github_private_key, transport)

    await create(client, first)
    await create(client, second)
    await create(client, first)

    assert transport.await_count == 5
    assert [call.args[1] for call in transport.call_args_list] == [
        TOKEN_URL,
        ISSUE_URL,
        TOKEN_URL,
        "https://api.github.com/repos/example-org/other-repo/issues",
        ISSUE_URL,
    ]
    token_payloads = [
        call.args[3] for call in transport.call_args_list if call.args[1] == TOKEN_URL
    ]
    assert [payload["repository_ids"] for payload in token_payloads] == [[222], [223]]


async def test_token_refreshed_near_expiry(
    github_private_key: rsa.RSAPrivateKey, route: TargetConfig
) -> None:
    transport = AsyncMock(
        side_effect=[token_response(), issue_response(), token_response(), issue_response()]
    )
    now = [EXPIRES_AT_EPOCH - 3600]
    client = make_client(github_private_key, transport, clock=lambda: now[0])

    await create(client, route)
    now[0] = EXPIRES_AT_EPOCH - 299
    await create(client, route)

    assert transport.await_count == 4
    assert [call.args[1] for call in transport.call_args_list] == [
        TOKEN_URL,
        ISSUE_URL,
        TOKEN_URL,
        ISSUE_URL,
    ]


async def test_token_request_401_raises(
    github_private_key: rsa.RSAPrivateKey, route: TargetConfig
) -> None:
    transport = AsyncMock(return_value=(401, {"message": "Secret error words"}))
    client = make_client(github_private_key, transport)

    with pytest.raises(GitHubError) as exc_info:
        await create(client, route)

    assert exc_info.value.stage == "token"
    assert exc_info.value.status == 401
    assert "Secret error words" not in str(exc_info.value)


@pytest.mark.parametrize("status", [403, 404, 410, 422, 500, 502])
async def test_issue_request_error_raises_without_text(
    github_private_key: rsa.RSAPrivateKey, route: TargetConfig, status: int
) -> None:
    error_body = {"message": "Validation Failed", "errors": [{"value": "Secret title words"}]}
    transport = AsyncMock(side_effect=[token_response(), (status, error_body)])
    client = make_client(github_private_key, transport)

    with pytest.raises(GitHubError) as exc_info:
        await create(client, route)

    exc = exc_info.value
    assert exc.stage == "issue"
    assert exc.status == status
    for text in (str(exc), repr(exc)):
        assert "Secret title words" not in text
        assert "ghs_secret_token" not in text


async def test_issue_request_401_drops_cached_token(
    github_private_key: rsa.RSAPrivateKey, route: TargetConfig
) -> None:
    transport = AsyncMock(
        side_effect=[token_response(), (401, None), token_response(), issue_response()]
    )
    client = make_client(github_private_key, transport)

    with pytest.raises(GitHubError) as exc_info:
        await create(client, route)
    assert (exc_info.value.stage, exc_info.value.status) == ("issue", 401)
    assert await create(client, route) == FiledIssue(7, HTML_URL, "I_node7")

    assert [call.args[1] for call in transport.call_args_list] == [
        TOKEN_URL,
        ISSUE_URL,
        TOKEN_URL,
        ISSUE_URL,
    ]


async def test_issue_request_404_keeps_cached_token(
    github_private_key: rsa.RSAPrivateKey, route: TargetConfig
) -> None:
    transport = AsyncMock(side_effect=[token_response(), (404, None), issue_response()])
    client = make_client(github_private_key, transport)

    with pytest.raises(GitHubError):
        await create(client, route)
    assert await create(client, route) == FiledIssue(7, HTML_URL, "I_node7")

    assert [call.args[1] for call in transport.call_args_list] == [
        TOKEN_URL,
        ISSUE_URL,
        ISSUE_URL,
    ]


@pytest.mark.parametrize(
    "response",
    [
        (201, None),
        (201, {"expires_at": EXPIRES_AT}),
        (201, {"token": 5, "expires_at": EXPIRES_AT}),
        (201, {"token": "t", "expires_at": "not-a-date"}),
        (201, {"token": "t", "expires_at": "2026-10-18T13:00:00"}),
    ],
)
async def test_bad_token_shape_raises(
    github_private_key: rsa.RSAPrivateKey, route: TargetConfig, response: tuple[int, Any]
) -> None:
    transport = AsyncMock(return_value=response)
    client = make_client(github_private_key, transport)

    with pytest.raises(GitHubError) as exc_info:
        await create(client, route)

    exc = exc_info.value
    assert exc.stage == "token"
    assert exc.status == 201
    assert exc.__cause__ is None
    assert exc.__suppress_context__ is True


@pytest.mark.parametrize(
    "error",
    [aiohttp.ClientConnectionError("Secret error words"), TimeoutError()],
    ids=["client-error", "timeout"],
)
@pytest.mark.parametrize("stage", ["token", "issue"])
async def test_transport_error_raises_status_none(
    github_private_key: rsa.RSAPrivateKey, route: TargetConfig, error: Exception, stage: str
) -> None:
    side_effect = error if stage == "token" else [token_response(), error]
    client = make_client(github_private_key, AsyncMock(side_effect=side_effect))

    with pytest.raises(GitHubError) as exc_info:
        await create(client, route)

    exc = exc_info.value
    assert exc.stage == stage
    assert exc.status is None
    assert exc.__cause__ is None
    assert exc.__context__ is None
    assert exc.__suppress_context__ is True
    assert "Secret error words" not in str(exc)


@pytest.mark.parametrize(
    "response",
    [
        (201, {"number": "x", "html_url": "u"}),
        (201, None),
        (201, {"number": True, "html_url": "u"}),
        (201, {"number": 7}),
        (201, {"number": 7, "html_url": HTML_URL}),
        (201, {"number": 7, "html_url": HTML_URL, "node_id": 5}),
    ],
)
async def test_bad_success_shape_raises(
    github_private_key: rsa.RSAPrivateKey, route: TargetConfig, response: tuple[int, Any]
) -> None:
    transport = AsyncMock(side_effect=[token_response(), response])
    client = make_client(github_private_key, transport)

    with pytest.raises(GitHubError) as exc_info:
        await create(client, route)

    assert exc_info.value.stage == "issue"
    assert exc_info.value.status == 201


async def test_client_repr_hides_secrets(
    github_private_key: rsa.RSAPrivateKey, route: TargetConfig
) -> None:
    transport = AsyncMock(side_effect=[token_response(), issue_response()])
    client = make_client(github_private_key, transport)
    await create(client, route)

    text = repr(client)
    assert text == "GitHubClient(app_id=333, installation_id=444)"
    assert "ghs_secret_token" not in text
    assert "PRIVATE KEY" not in text
    assert "RSAPrivateKey" not in text


async def test_default_transport_is_guarded(
    github_private_key: rsa.RSAPrivateKey, route: TargetConfig
) -> None:
    client = GitHubClient(333, 444, github_private_key)

    with pytest.raises(AssertionError, match="live GitHub call in a test"):
        await create(client, route)


async def test_check_access_mints_a_token(
    github_private_key: rsa.RSAPrivateKey, route: TargetConfig
) -> None:
    transport = AsyncMock(side_effect=[token_response()])
    client = make_client(github_private_key, transport)

    await client.check_access(route)

    assert transport.await_count == 1
    method, url, _headers, payload = transport.call_args.args
    assert (method, url) == ("POST", TOKEN_URL)
    assert payload == {"repository_ids": [222], "permissions": {"issues": "write"}}


PROJECT_TOKEN_PAYLOAD = {
    "repository_ids": [222],
    "permissions": {"issues": "write", "organization_projects": "write"},
}


async def test_check_access_project_route_asks_for_projects(
    github_private_key: rsa.RSAPrivateKey, project_route: TargetConfig
) -> None:
    transport = AsyncMock(side_effect=[token_response()])
    client = make_client(github_private_key, transport)

    await client.check_access(project_route)

    assert transport.await_count == 1
    method, url, _headers, payload = transport.call_args.args
    assert (method, url) == ("POST", TOKEN_URL)
    assert payload == PROJECT_TOKEN_PAYLOAD


async def test_create_issue_project_route_asks_for_projects(
    github_private_key: rsa.RSAPrivateKey, project_route: TargetConfig
) -> None:
    transport = AsyncMock(side_effect=[token_response(), issue_response()])
    client = make_client(github_private_key, transport)

    assert await create(client, project_route) == FiledIssue(7, HTML_URL, "I_node7")

    token_call, issue_call = transport.call_args_list
    assert token_call.args[1] == TOKEN_URL
    assert token_call.args[3] == PROJECT_TOKEN_PAYLOAD
    assert issue_call.args[1] == ISSUE_URL


async def test_plain_and_project_route_mint_separate_tokens(
    github_private_key: rsa.RSAPrivateKey, route: TargetConfig, project_route: TargetConfig
) -> None:
    transport = AsyncMock(side_effect=[token_response(), token_response()])
    client = make_client(github_private_key, transport)

    await client.check_access(route)
    await client.check_access(project_route)
    await client.check_access(route)
    await client.check_access(project_route)

    assert transport.await_count == 2
    assert [call.args[3] for call in transport.call_args_list] == [
        {"repository_ids": [222], "permissions": {"issues": "write"}},
        PROJECT_TOKEN_PAYLOAD,
    ]


async def test_issue_401_on_project_route_drops_only_its_token(
    github_private_key: rsa.RSAPrivateKey, route: TargetConfig, project_route: TargetConfig
) -> None:
    transport = AsyncMock(
        side_effect=[
            token_response(),
            token_response(),
            (401, None),
            issue_response(),
            token_response(),
            issue_response(),
        ]
    )
    client = make_client(github_private_key, transport)

    await client.check_access(route)
    await client.check_access(project_route)
    with pytest.raises(GitHubError) as exc_info:
        await create(client, project_route)
    assert (exc_info.value.stage, exc_info.value.status) == ("issue", 401)
    await create(client, route)
    await create(client, project_route)

    assert [call.args[1] for call in transport.call_args_list] == [
        TOKEN_URL,
        TOKEN_URL,
        ISSUE_URL,
        ISSUE_URL,
        TOKEN_URL,
        ISSUE_URL,
    ]
    assert transport.call_args_list[4].args[3] == PROJECT_TOKEN_PAYLOAD


async def test_check_access_reuses_cached_token(
    github_private_key: rsa.RSAPrivateKey, route: TargetConfig
) -> None:
    transport = AsyncMock(side_effect=[token_response()])
    client = make_client(github_private_key, transport, clock=lambda: EXPIRES_AT_EPOCH - 301)

    await client.check_access(route)
    await client.check_access(route)

    assert transport.await_count == 1


async def test_check_access_token_error_raises(
    github_private_key: rsa.RSAPrivateKey, route: TargetConfig
) -> None:
    transport = AsyncMock(return_value=(404, {"message": "Secret error words"}))
    client = make_client(github_private_key, transport)

    with pytest.raises(GitHubError) as exc_info:
        await client.check_access(route)

    assert (exc_info.value.stage, exc_info.value.status) == ("token", 404)
    assert "Secret error words" not in str(exc_info.value)


async def test_check_access_transport_error_raises_status_none(
    github_private_key: rsa.RSAPrivateKey, route: TargetConfig
) -> None:
    transport = AsyncMock(side_effect=aiohttp.ClientConnectionError("Secret error words"))
    client = make_client(github_private_key, transport)

    with pytest.raises(GitHubError) as exc_info:
        await client.check_access(route)

    assert (exc_info.value.stage, exc_info.value.status) == ("token", None)


async def test_ensure_label_creates_label(
    github_private_key: rsa.RSAPrivateKey, route: TargetConfig
) -> None:
    transport = AsyncMock(side_effect=[token_response(), (201, {"name": "complexity:M"})])
    client = make_client(github_private_key, transport)

    await client.ensure_label(route, "complexity:M")

    assert transport.await_count == 2
    method, url, headers, payload = transport.call_args_list[1].args
    assert (method, url) == ("POST", LABEL_URL)
    assert payload == {"name": "complexity:M", "color": LABEL_COLOR}
    assert headers["Authorization"] == "Bearer ghs_secret_token"


async def test_ensure_label_422_is_success(
    github_private_key: rsa.RSAPrivateKey, route: TargetConfig
) -> None:
    transport = AsyncMock(side_effect=[token_response(), (422, {"message": "already_exists"})])
    client = make_client(github_private_key, transport)

    await client.ensure_label(route, "complexity:M")

    assert transport.await_count == 2


async def test_ensure_label_is_cached_per_name(
    github_private_key: rsa.RSAPrivateKey, route: TargetConfig
) -> None:
    transport = AsyncMock(side_effect=[token_response(), (201, {}), (201, {})])
    client = make_client(github_private_key, transport, clock=lambda: EXPIRES_AT_EPOCH - 301)

    await client.ensure_label(route, "complexity:M")
    await client.ensure_label(route, "complexity:M")
    assert transport.await_count == 2

    await client.ensure_label(route, "complexity:L")
    assert transport.await_count == 3
    assert transport.call_args_list[2].args[1] == LABEL_URL
    assert transport.call_args_list[2].args[3]["name"] == "complexity:L"


async def test_ensure_label_is_cached_per_repo(
    github_private_key: rsa.RSAPrivateKey, two_route_config: Config
) -> None:
    first, second = two_route_config.routes.values()
    transport = AsyncMock(
        side_effect=[token_response(), (201, {}), token_response(), (201, {})]
    )
    client = make_client(github_private_key, transport)

    await client.ensure_label(first, "complexity:S")
    await client.ensure_label(second, "complexity:S")

    assert transport.await_count == 4
    assert [call.args[1] for call in transport.call_args_list] == [
        TOKEN_URL,
        LABEL_URL,
        TOKEN_URL,
        "https://api.github.com/repos/example-org/other-repo/labels",
    ]


async def test_ensure_label_401_drops_cached_token(
    github_private_key: rsa.RSAPrivateKey, route: TargetConfig
) -> None:
    transport = AsyncMock(
        side_effect=[token_response(), (401, None), token_response(), (201, {})]
    )
    client = make_client(github_private_key, transport)

    with pytest.raises(GitHubError) as exc_info:
        await client.ensure_label(route, "complexity:M")
    assert (exc_info.value.stage, exc_info.value.status) == ("label", 401)
    await client.ensure_label(route, "complexity:M")

    assert [call.args[1] for call in transport.call_args_list] == [
        TOKEN_URL,
        LABEL_URL,
        TOKEN_URL,
        LABEL_URL,
    ]


async def test_ensure_label_401_on_project_route_drops_only_its_token(
    github_private_key: rsa.RSAPrivateKey, route: TargetConfig, project_route: TargetConfig
) -> None:
    transport = AsyncMock(
        side_effect=[
            token_response(),
            token_response(),
            (401, None),
            (201, {}),
            token_response(),
            (201, {}),
        ]
    )
    client = make_client(github_private_key, transport)

    await client.check_access(route)
    await client.check_access(project_route)
    with pytest.raises(GitHubError) as exc_info:
        await client.ensure_label(project_route, "complexity:M")
    assert (exc_info.value.stage, exc_info.value.status) == ("label", 401)
    await client.ensure_label(route, "complexity:M")
    await client.ensure_label(project_route, "complexity:L")

    assert [call.args[1] for call in transport.call_args_list] == [
        TOKEN_URL,
        TOKEN_URL,
        LABEL_URL,
        LABEL_URL,
        TOKEN_URL,
        LABEL_URL,
    ]
    assert transport.call_args_list[4].args[3] == PROJECT_TOKEN_PAYLOAD


async def test_ensure_label_500_raises_and_is_not_cached(
    github_private_key: rsa.RSAPrivateKey, route: TargetConfig
) -> None:
    error_body = {"message": "Secret error words"}
    transport = AsyncMock(side_effect=[token_response(), (500, error_body), (201, {})])
    client = make_client(github_private_key, transport)

    with pytest.raises(GitHubError) as exc_info:
        await client.ensure_label(route, "complexity:M")
    exc = exc_info.value
    assert (exc.stage, exc.status) == ("label", 500)
    assert exc.__cause__ is None
    assert exc.__suppress_context__ is True
    assert "Secret error words" not in str(exc)

    await client.ensure_label(route, "complexity:M")
    assert [call.args[1] for call in transport.call_args_list] == [
        TOKEN_URL,
        LABEL_URL,
        LABEL_URL,
    ]


async def test_ensure_label_transport_error_raises_status_none(
    github_private_key: rsa.RSAPrivateKey, route: TargetConfig
) -> None:
    error = aiohttp.ClientConnectionError("Secret error words")
    transport = AsyncMock(side_effect=[token_response(), error, (201, {})])
    client = make_client(github_private_key, transport)

    with pytest.raises(GitHubError) as exc_info:
        await client.ensure_label(route, "complexity:M")
    exc = exc_info.value
    assert (exc.stage, exc.status) == ("label", None)
    assert exc.__context__ is None
    assert "Secret error words" not in str(exc)

    await client.ensure_label(route, "complexity:M")
    assert transport.await_count == 3


PROJECT_FIELDS = ProjectFields(
    project_id="PVT_1",
    status_field_id="F_status",
    status_option_id="O_todo",
    effort_field_id="F_effort",
    effort_option_ids={"S": "O_s", "M": "O_m", "L": "O_l", "XL": "O_xl"},
)
ISSUE = FiledIssue(7, HTML_URL, "I_node7")


def status_field(options: list[str] | None = None) -> dict[str, Any]:
    names = ["Todo", "In Progress", "Done"] if options is None else options
    ids = {"Todo": "O_todo", "In Progress": "O_prog", "Done": "O_done"}
    return {
        "id": "F_status",
        "name": "Status",
        "options": [{"id": ids.get(name, f"O_{name}"), "name": name} for name in names],
    }


def effort_field(options: list[str] | None = None) -> dict[str, Any]:
    names = ["S", "M", "L", "XL", "XXL"] if options is None else options
    return {
        "id": "F_effort",
        "name": "Effort",
        "options": [{"id": f"O_{name.lower()}", "name": name} for name in names],
    }


TRACK_OPTION_IDS = {"A · Bugs": "O_t0", "B · Form & feedback": "O_t1"}


def track_field(options: list[str] | None = None) -> dict[str, Any]:
    names = list(TRACK_OPTION_IDS) if options is None else options
    return {
        "id": "F_track",
        "name": "Track",
        "options": [
            {"id": TRACK_OPTION_IDS.get(name, f"O_{name}"), "name": name} for name in names
        ],
    }


def project_response(
    nodes: list[Any] | None = None,
) -> tuple[int, dict[str, Any]]:
    if nodes is None:
        nodes = [
            None,
            {},
            {"id": "F_title", "name": "Title"},
            status_field(),
            {"id": "F_other", "name": "Priority", "options": [{"id": "O_hi", "name": "High"}]},
            effort_field(),
        ]
    return 200, {
        "data": {"organization": {"projectV2": {"id": "PVT_1", "fields": {"nodes": nodes}}}}
    }


def add_response() -> tuple[int, dict[str, Any]]:
    return 200, {"data": {"addProjectV2ItemById": {"item": {"id": "PVTI_1"}}}}


def set_response() -> tuple[int, dict[str, Any]]:
    return 200, {
        "data": {
            "status": {"projectV2Item": {"id": "PVTI_1"}},
            "effort": {"projectV2Item": {"id": "PVTI_1"}},
        }
    }


ERRORS_RESPONSE = (200, {"errors": [{"message": "Secret detail"}]})


async def test_project_fields_looks_up_and_caches(
    github_private_key: rsa.RSAPrivateKey, project_route: TargetConfig
) -> None:
    transport = AsyncMock(side_effect=[token_response(), project_response()])
    client = make_client(github_private_key, transport)

    fields = await client.project_fields(project_route)
    again = await client.project_fields(project_route)

    assert fields == PROJECT_FIELDS
    assert again == PROJECT_FIELDS
    assert transport.await_count == 2
    token_call, lookup_call = transport.call_args_list
    assert token_call.args[3] == PROJECT_TOKEN_PAYLOAD
    method, url, headers, payload = lookup_call.args
    assert (method, url) == ("POST", GRAPHQL_URL)
    assert headers["Authorization"] == "Bearer ghs_secret_token"
    assert payload == {
        "query": PROJECT_FIELDS_QUERY,
        "variables": {"org": "example-org", "number": 2},
    }


async def test_project_fields_effort_options_are_frozen(
    github_private_key: rsa.RSAPrivateKey, project_route: TargetConfig
) -> None:
    transport = AsyncMock(side_effect=[token_response(), project_response()])
    client = make_client(github_private_key, transport)

    fields = await client.project_fields(project_route)

    with pytest.raises(TypeError):
        fields.effort_option_ids["S"] = "O_other"  # type: ignore[index]


async def test_project_fields_without_project_raises_value_error(
    github_private_key: rsa.RSAPrivateKey, route: TargetConfig
) -> None:
    transport = AsyncMock()
    client = make_client(github_private_key, transport)

    with pytest.raises(ValueError, match="route has no project"):
        await client.project_fields(route)

    assert transport.await_count == 0


@pytest.mark.parametrize(
    "response",
    [
        ERRORS_RESPONSE,
        (200, {"data": {"organization": {"projectV2": None}}}),
        (200, {"data": {"organization": None}}),
        (200, {"data": None}),
        (200, None),
        (200, {"data": {"organization": {"projectV2": {"id": 5, "fields": {"nodes": []}}}}}),
        (200, {"data": {"organization": {"projectV2": {"id": "PVT_1", "fields": None}}}}),
        project_response([effort_field()]),
        project_response([status_field(["In Progress", "Done"]), effort_field()]),
        project_response([status_field()]),
        project_response([status_field(), effort_field(["S", "M", "L"])]),
        project_response([{"id": "F_status", "name": "Status", "options": None}, effort_field()]),
    ],
    ids=[
        "errors",
        "null-project",
        "null-organization",
        "null-data",
        "null-body",
        "bad-project-id",
        "null-fields",
        "no-status-field",
        "no-status-option",
        "no-effort-field",
        "effort-missing-band",
        "null-options",
    ],
)
async def test_project_fields_bad_response_raises(
    github_private_key: rsa.RSAPrivateKey,
    project_route: TargetConfig,
    response: tuple[int, Any],
) -> None:
    transport = AsyncMock(side_effect=[token_response(), response, project_response()])
    client = make_client(github_private_key, transport)

    with pytest.raises(GitHubError) as exc_info:
        await client.project_fields(project_route)

    exc = exc_info.value
    assert (exc.stage, exc.status) == ("project", 200)
    assert exc.__cause__ is None
    assert exc.__suppress_context__ is True
    assert "Secret detail" not in str(exc)
    assert "Secret detail" not in repr(exc)
    # A failed lookup is never cached: the next call requests again.
    assert await client.project_fields(project_route) == PROJECT_FIELDS
    assert transport.await_count == 3


async def test_project_fields_non_200_raises(
    github_private_key: rsa.RSAPrivateKey, project_route: TargetConfig
) -> None:
    transport = AsyncMock(side_effect=[token_response(), (502, {"message": "Secret detail"})])
    client = make_client(github_private_key, transport)

    with pytest.raises(GitHubError) as exc_info:
        await client.project_fields(project_route)

    assert (exc_info.value.stage, exc_info.value.status) == ("project", 502)
    assert "Secret detail" not in str(exc_info.value)
    assert "Secret detail" not in repr(exc_info.value)


async def test_project_fields_401_drops_token(
    github_private_key: rsa.RSAPrivateKey, project_route: TargetConfig
) -> None:
    transport = AsyncMock(
        side_effect=[token_response(), (401, None), token_response(), project_response()]
    )
    client = make_client(github_private_key, transport)

    with pytest.raises(GitHubError) as exc_info:
        await client.project_fields(project_route)
    assert (exc_info.value.stage, exc_info.value.status) == ("project", 401)

    assert await client.project_fields(project_route) == PROJECT_FIELDS
    assert [call.args[1] for call in transport.call_args_list] == [
        TOKEN_URL,
        GRAPHQL_URL,
        TOKEN_URL,
        GRAPHQL_URL,
    ]


async def test_add_to_project_adds_and_sets_fields(
    github_private_key: rsa.RSAPrivateKey, project_route: TargetConfig
) -> None:
    transport = AsyncMock(
        side_effect=[token_response(), project_response(), add_response(), set_response()]
    )
    client = make_client(github_private_key, transport)

    assert await client.add_to_project(project_route, ISSUE, Complexity.M) == "PVTI_1"

    assert transport.await_count == 4
    token_call, lookup_call, add_call, set_call = transport.call_args_list
    assert token_call.args[3] == PROJECT_TOKEN_PAYLOAD
    assert lookup_call.args[3]["query"] == PROJECT_FIELDS_QUERY
    for call in (lookup_call, add_call, set_call):
        method, url, headers, _payload = call.args
        assert (method, url) == ("POST", GRAPHQL_URL)
        assert headers["Authorization"] == "Bearer ghs_secret_token"
    add_payload = add_call.args[3]
    assert "addProjectV2ItemById" in add_payload["query"]
    assert add_payload["variables"] == {"project": "PVT_1", "content": "I_node7"}
    set_payload = set_call.args[3]
    assert set_payload["query"].count("updateProjectV2ItemFieldValue") == 2
    assert set_payload["variables"] == {
        "project": "PVT_1",
        "item": "PVTI_1",
        "statusField": "F_status",
        "status": "O_todo",
        "effortField": "F_effort",
        "effort": "O_m",
    }


@pytest.mark.parametrize(
    "response",
    [
        ERRORS_RESPONSE,
        (200, {"data": {"addProjectV2ItemById": {"item": None}}}),
        (200, {"data": {"addProjectV2ItemById": {"item": {"id": 5}}}}),
        (200, {"data": {"addProjectV2ItemById": None}}),
    ],
    ids=["errors", "null-item", "bad-item-id", "null-add"],
)
async def test_add_to_project_bad_add_raises(
    github_private_key: rsa.RSAPrivateKey,
    project_route: TargetConfig,
    response: tuple[int, Any],
) -> None:
    transport = AsyncMock(side_effect=[token_response(), project_response(), response])
    client = make_client(github_private_key, transport)

    with pytest.raises(GitHubError) as exc_info:
        await client.add_to_project(project_route, ISSUE, Complexity.M)

    exc = exc_info.value
    assert (exc.stage, exc.status) == ("project-item", 200)
    assert exc.__cause__ is None
    assert "Secret detail" not in str(exc)
    assert "Secret detail" not in repr(exc)


@pytest.mark.parametrize(
    "response",
    [
        ERRORS_RESPONSE,
        (200, {"data": {"status": None, "effort": {"projectV2Item": {"id": "PVTI_1"}}}}),
        (200, {"data": {"status": {"projectV2Item": {"id": "PVTI_1"}}, "effort": None}}),
        (200, {"data": {"status": {"projectV2Item": None}, "effort": {"projectV2Item": {}}}}),
    ],
    ids=["errors", "null-status", "null-effort", "null-item"],
)
async def test_add_to_project_bad_set_raises(
    github_private_key: rsa.RSAPrivateKey,
    project_route: TargetConfig,
    response: tuple[int, Any],
) -> None:
    transport = AsyncMock(
        side_effect=[token_response(), project_response(), add_response(), response]
    )
    client = make_client(github_private_key, transport)

    with pytest.raises(GitHubError) as exc_info:
        await client.add_to_project(project_route, ISSUE, Complexity.M)

    exc = exc_info.value
    assert (exc.stage, exc.status) == ("project-field", 200)
    assert exc.__cause__ is None
    assert "Secret detail" not in str(exc)
    assert "Secret detail" not in repr(exc)


@pytest.mark.parametrize(
    ("failing_call", "stage"),
    [(1, "project"), (2, "project-item"), (3, "project-field")],
)
async def test_add_to_project_transport_error_raises_status_none(
    github_private_key: rsa.RSAPrivateKey,
    project_route: TargetConfig,
    failing_call: int,
    stage: str,
) -> None:
    responses: list[Any] = [token_response(), project_response(), add_response(), set_response()]
    responses[failing_call] = aiohttp.ClientConnectionError("Secret error words")
    client = make_client(github_private_key, AsyncMock(side_effect=responses[: failing_call + 1]))

    with pytest.raises(GitHubError) as exc_info:
        await client.add_to_project(project_route, ISSUE, Complexity.M)

    exc = exc_info.value
    assert (exc.stage, exc.status) == (stage, None)
    assert exc.__context__ is None
    assert "Secret error words" not in str(exc)


async def test_failed_set_drops_cached_project_ids(
    github_private_key: rsa.RSAPrivateKey, project_route: TargetConfig
) -> None:
    transport = AsyncMock(
        side_effect=[
            token_response(),
            project_response(),
            add_response(),
            ERRORS_RESPONSE,
            project_response(),
            add_response(),
            set_response(),
        ]
    )
    client = make_client(github_private_key, transport)

    with pytest.raises(GitHubError) as exc_info:
        await client.add_to_project(project_route, ISSUE, Complexity.M)
    assert (exc_info.value.stage, exc_info.value.status) == ("project-field", 200)
    await client.add_to_project(project_route, ISSUE, Complexity.M)

    calls = transport.call_args_list
    assert len(calls) == 7
    assert calls[4].args[3]["query"] == PROJECT_FIELDS_QUERY
    assert "addProjectV2ItemById" in calls[5].args[3]["query"]
    assert "updateProjectV2ItemFieldValue" in calls[6].args[3]["query"]


async def test_failed_add_drops_cached_project_ids(
    github_private_key: rsa.RSAPrivateKey, project_route: TargetConfig
) -> None:
    transport = AsyncMock(
        side_effect=[
            token_response(),
            project_response(),
            ERRORS_RESPONSE,
            project_response(),
            add_response(),
            set_response(),
        ]
    )
    client = make_client(github_private_key, transport)

    with pytest.raises(GitHubError) as exc_info:
        await client.add_to_project(project_route, ISSUE, Complexity.M)
    assert (exc_info.value.stage, exc_info.value.status) == ("project-item", 200)
    await client.add_to_project(project_route, ISSUE, Complexity.M)

    calls = transport.call_args_list
    assert len(calls) == 6
    assert calls[3].args[3]["query"] == PROJECT_FIELDS_QUERY


async def test_successful_add_keeps_cached_project_ids(
    github_private_key: rsa.RSAPrivateKey, project_route: TargetConfig
) -> None:
    transport = AsyncMock(
        side_effect=[
            token_response(),
            project_response(),
            add_response(),
            set_response(),
            add_response(),
            set_response(),
        ]
    )
    client = make_client(github_private_key, transport)

    assert await client.add_to_project(project_route, ISSUE, Complexity.M) == "PVTI_1"
    assert await client.add_to_project(project_route, ISSUE, Complexity.XL) == "PVTI_1"

    calls = transport.call_args_list
    assert len(calls) == 6
    assert calls[5].args[3]["variables"]["effort"] == "O_xl"



@pytest.fixture
def track_route(project_route: TargetConfig) -> TargetConfig:
    """The project route with a Track field configured."""
    assert project_route.project is not None
    return replace(project_route, project=replace(project_route.project, track_field="Track"))


def track_project_response(options: list[str] | None = None) -> tuple[int, dict[str, Any]]:
    return project_response([status_field(), effort_field(), track_field(options)])


def set_track_response() -> tuple[int, dict[str, Any]]:
    return 200, {"data": {"track": {"projectV2Item": {"id": "PVTI_1"}}}}


async def test_project_fields_reads_track_options(
    github_private_key: rsa.RSAPrivateKey, track_route: TargetConfig
) -> None:
    transport = AsyncMock(side_effect=[token_response(), track_project_response()])
    client = make_client(github_private_key, transport)

    fields = await client.project_fields(track_route)

    assert fields == replace(
        PROJECT_FIELDS, track_field_id="F_track", track_option_ids=TRACK_OPTION_IDS
    )
    with pytest.raises(TypeError):
        fields.track_option_ids["A · Bugs"] = "O_other"  # type: ignore[index]


async def test_project_fields_keeps_track_options_in_project_order(
    github_private_key: rsa.RSAPrivateKey, track_route: TargetConfig
) -> None:
    transport = AsyncMock(
        side_effect=[
            token_response(),
            track_project_response(["B · Form & feedback", "A · Bugs"]),
        ]
    )
    client = make_client(github_private_key, transport)

    fields = await client.project_fields(track_route)

    assert tuple(fields.track_option_ids) == ("B · Form & feedback", "A · Bugs")


@pytest.mark.parametrize(
    "track_node",
    [None, {"id": "F_track", "name": "Track", "options": None}],
    ids=["no-track-field", "malformed-track-field"],
)
async def test_project_fields_missing_track_field_is_no_track(
    github_private_key: rsa.RSAPrivateKey,
    track_route: TargetConfig,
    track_node: dict[str, Any] | None,
) -> None:
    nodes: list[Any] = [status_field(), effort_field()]
    if track_node is not None:
        nodes.append(track_node)
    transport = AsyncMock(side_effect=[token_response(), project_response(nodes)])
    client = make_client(github_private_key, transport)

    fields = await client.project_fields(track_route)
    again = await client.project_fields(track_route)

    assert fields.track_field_id is None
    assert fields.track_option_ids == {}
    assert again is fields
    assert transport.await_count == 2


async def test_project_fields_without_track_field_config_ignores_track_node(
    github_private_key: rsa.RSAPrivateKey, project_route: TargetConfig
) -> None:
    transport = AsyncMock(side_effect=[token_response(), track_project_response()])
    client = make_client(github_private_key, transport)

    fields = await client.project_fields(project_route)

    assert fields == PROJECT_FIELDS
    assert fields.track_field_id is None
    assert fields.track_option_ids == {}


async def test_track_options_returns_names_and_reuses_cache(
    github_private_key: rsa.RSAPrivateKey, track_route: TargetConfig
) -> None:
    transport = AsyncMock(side_effect=[token_response(), track_project_response()])
    client = make_client(github_private_key, transport)

    assert await client.track_options(track_route) == ("A · Bugs", "B · Form & feedback")
    assert await client.track_options(track_route) == ("A · Bugs", "B · Form & feedback")
    assert transport.await_count == 2


async def test_track_options_keeps_project_order(
    github_private_key: rsa.RSAPrivateKey, track_route: TargetConfig
) -> None:
    transport = AsyncMock(
        side_effect=[
            token_response(),
            track_project_response(["B · Form & feedback", "A · Bugs"]),
        ]
    )
    client = make_client(github_private_key, transport)

    assert await client.track_options(track_route) == ("B · Form & feedback", "A · Bugs")


async def test_track_options_empty_without_track_field(
    github_private_key: rsa.RSAPrivateKey, track_route: TargetConfig
) -> None:
    transport = AsyncMock(side_effect=[token_response(), project_response()])
    client = make_client(github_private_key, transport)

    assert await client.track_options(track_route) == ()


async def test_track_options_empty_for_route_without_project(
    github_private_key: rsa.RSAPrivateKey, route: TargetConfig
) -> None:
    transport = AsyncMock()
    client = make_client(github_private_key, transport)
    client.project_fields = AsyncMock()  # type: ignore[method-assign]

    assert await client.track_options(route) == ()
    client.project_fields.assert_not_awaited()
    assert transport.await_count == 0


async def test_set_track_sets_the_option(
    github_private_key: rsa.RSAPrivateKey, track_route: TargetConfig
) -> None:
    transport = AsyncMock(
        side_effect=[token_response(), track_project_response(), set_track_response()]
    )
    client = make_client(github_private_key, transport)

    assert await client.set_track(track_route, "PVTI_1", "B · Form & feedback") is None

    assert transport.await_count == 3
    method, url, headers, payload = transport.call_args_list[2].args
    assert (method, url) == ("POST", GRAPHQL_URL)
    assert headers["Authorization"] == "Bearer ghs_secret_token"
    assert payload == {
        "query": SET_TRACK_MUTATION,
        "variables": {
            "project": "PVT_1",
            "item": "PVTI_1",
            "field": "F_track",
            "option": "O_t1",
        },
    }


@pytest.mark.parametrize(
    ("lookup", "track"),
    [
        (track_project_response(), "Z · Unknown"),
        (project_response(), "A · Bugs"),
    ],
    ids=["unknown-option", "no-track-field"],
)
async def test_set_track_without_option_raises_before_request(
    github_private_key: rsa.RSAPrivateKey,
    track_route: TargetConfig,
    lookup: tuple[int, dict[str, Any]],
    track: str,
) -> None:
    transport = AsyncMock(side_effect=[token_response(), lookup, track_project_response()])
    client = make_client(github_private_key, transport)
    await client.track_options(track_route)

    with pytest.raises(GitHubError) as exc_info:
        await client.set_track(track_route, "PVTI_1", track)

    exc = exc_info.value
    assert (exc.stage, exc.status) == ("project-track", 200)
    assert exc.__cause__ is None
    assert transport.await_count == 2
    assert all(
        call.args[3].get("query") != SET_TRACK_MUTATION for call in transport.call_args_list
    )
    # The cached ids were dropped: the next lookup requests again.
    await client.track_options(track_route)
    assert transport.await_count == 3
    assert transport.call_args_list[2].args[3]["query"] == PROJECT_FIELDS_QUERY


@pytest.mark.parametrize(
    ("response", "status"),
    [
        (ERRORS_RESPONSE, 200),
        ((200, {"data": {"track": None}}), 200),
        ((200, {"data": {"track": {"projectV2Item": None}}}), 200),
        ((200, {"data": {}}), 200),
        (aiohttp.ClientConnectionError("Secret detail"), None),
    ],
    ids=["errors", "null-track", "null-item", "no-alias", "transport"],
)
async def test_set_track_failure_raises_and_drops_cached_ids(
    github_private_key: rsa.RSAPrivateKey,
    track_route: TargetConfig,
    response: Any,
    status: int | None,
) -> None:
    transport = AsyncMock(
        side_effect=[
            token_response(),
            track_project_response(),
            response,
            track_project_response(),
            set_track_response(),
        ]
    )
    client = make_client(github_private_key, transport)

    with pytest.raises(GitHubError) as exc_info:
        await client.set_track(track_route, "PVTI_1", "A · Bugs")

    exc = exc_info.value
    assert (exc.stage, exc.status) == ("project-track", status)
    assert exc.__cause__ is None
    # The transport error's frames hold the bearer token, so it is never chained.
    assert exc.__context__ is None
    assert "Secret detail" not in str(exc)
    assert "Secret detail" not in repr(exc)

    await client.set_track(track_route, "PVTI_1", "A · Bugs")
    calls = transport.call_args_list
    assert len(calls) == 5
    assert calls[3].args[3]["query"] == PROJECT_FIELDS_QUERY
    assert calls[4].args[3]["query"] == SET_TRACK_MUTATION
