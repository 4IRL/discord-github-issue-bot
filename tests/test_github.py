from collections.abc import Callable
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock

import aiohttp
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from issue_bot.config import Config
from issue_bot.github import FiledIssue, GitHubClient, GitHubError, Transport, app_jwt

TOKEN_URL = "https://api.github.com/app/installations/444/access_tokens"
ISSUE_URL = "https://api.github.com/repos/example-org/example-repo/issues"
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
    return 201, {"number": 7, "html_url": HTML_URL}


async def create(client: GitHubClient, config: Config) -> FiledIssue:
    return await client.create_issue(config.target, "Title", "Body", ["bug"])


async def test_create_issue_success(
    github_private_key: rsa.RSAPrivateKey, config: Config
) -> None:
    transport = AsyncMock(side_effect=[token_response(), issue_response()])
    client = make_client(github_private_key, transport)

    result = await client.create_issue(config.target, "Title", "Body", ["bug"])

    assert result == FiledIssue(7, HTML_URL)
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
    github_private_key: rsa.RSAPrivateKey, config: Config
) -> None:
    transport = AsyncMock(side_effect=[token_response(), issue_response(), issue_response()])
    client = make_client(github_private_key, transport, clock=lambda: EXPIRES_AT_EPOCH - 301)

    await create(client, config)
    await create(client, config)

    assert transport.await_count == 3
    assert [call.args[1] for call in transport.call_args_list] == [
        TOKEN_URL,
        ISSUE_URL,
        ISSUE_URL,
    ]


async def test_token_refreshed_near_expiry(
    github_private_key: rsa.RSAPrivateKey, config: Config
) -> None:
    transport = AsyncMock(
        side_effect=[token_response(), issue_response(), token_response(), issue_response()]
    )
    now = [EXPIRES_AT_EPOCH - 3600]
    client = make_client(github_private_key, transport, clock=lambda: now[0])

    await create(client, config)
    now[0] = EXPIRES_AT_EPOCH - 299
    await create(client, config)

    assert transport.await_count == 4
    assert [call.args[1] for call in transport.call_args_list] == [
        TOKEN_URL,
        ISSUE_URL,
        TOKEN_URL,
        ISSUE_URL,
    ]


async def test_token_request_401_raises(
    github_private_key: rsa.RSAPrivateKey, config: Config
) -> None:
    transport = AsyncMock(return_value=(401, {"message": "Secret error words"}))
    client = make_client(github_private_key, transport)

    with pytest.raises(GitHubError) as exc_info:
        await create(client, config)

    assert exc_info.value.stage == "token"
    assert exc_info.value.status == 401
    assert "Secret error words" not in str(exc_info.value)


@pytest.mark.parametrize("status", [403, 404, 410, 422, 500, 502])
async def test_issue_request_error_raises_without_text(
    github_private_key: rsa.RSAPrivateKey, config: Config, status: int
) -> None:
    error_body = {"message": "Validation Failed", "errors": [{"value": "Secret title words"}]}
    transport = AsyncMock(side_effect=[token_response(), (status, error_body)])
    client = make_client(github_private_key, transport)

    with pytest.raises(GitHubError) as exc_info:
        await create(client, config)

    exc = exc_info.value
    assert exc.stage == "issue"
    assert exc.status == status
    for text in (str(exc), repr(exc)):
        assert "Secret title words" not in text
        assert "ghs_secret_token" not in text


async def test_issue_request_401_drops_cached_token(
    github_private_key: rsa.RSAPrivateKey, config: Config
) -> None:
    transport = AsyncMock(
        side_effect=[token_response(), (401, None), token_response(), issue_response()]
    )
    client = make_client(github_private_key, transport)

    with pytest.raises(GitHubError) as exc_info:
        await create(client, config)
    assert (exc_info.value.stage, exc_info.value.status) == ("issue", 401)
    assert await create(client, config) == FiledIssue(7, HTML_URL)

    assert [call.args[1] for call in transport.call_args_list] == [
        TOKEN_URL,
        ISSUE_URL,
        TOKEN_URL,
        ISSUE_URL,
    ]


async def test_issue_request_404_keeps_cached_token(
    github_private_key: rsa.RSAPrivateKey, config: Config
) -> None:
    transport = AsyncMock(side_effect=[token_response(), (404, None), issue_response()])
    client = make_client(github_private_key, transport)

    with pytest.raises(GitHubError):
        await create(client, config)
    assert await create(client, config) == FiledIssue(7, HTML_URL)

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
    github_private_key: rsa.RSAPrivateKey, config: Config, response: tuple[int, Any]
) -> None:
    transport = AsyncMock(return_value=response)
    client = make_client(github_private_key, transport)

    with pytest.raises(GitHubError) as exc_info:
        await create(client, config)

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
    github_private_key: rsa.RSAPrivateKey, config: Config, error: Exception, stage: str
) -> None:
    side_effect = error if stage == "token" else [token_response(), error]
    client = make_client(github_private_key, AsyncMock(side_effect=side_effect))

    with pytest.raises(GitHubError) as exc_info:
        await create(client, config)

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
    ],
)
async def test_bad_success_shape_raises(
    github_private_key: rsa.RSAPrivateKey, config: Config, response: tuple[int, Any]
) -> None:
    transport = AsyncMock(side_effect=[token_response(), response])
    client = make_client(github_private_key, transport)

    with pytest.raises(GitHubError) as exc_info:
        await create(client, config)

    assert exc_info.value.stage == "issue"
    assert exc_info.value.status == 201


async def test_client_repr_hides_secrets(
    github_private_key: rsa.RSAPrivateKey, config: Config
) -> None:
    transport = AsyncMock(side_effect=[token_response(), issue_response()])
    client = make_client(github_private_key, transport)
    await create(client, config)

    text = repr(client)
    assert text == "GitHubClient(app_id=333, installation_id=444)"
    assert "ghs_secret_token" not in text
    assert "PRIVATE KEY" not in text
    assert "RSAPrivateKey" not in text


async def test_default_transport_is_guarded(
    github_private_key: rsa.RSAPrivateKey, config: Config
) -> None:
    client = GitHubClient(333, 444, github_private_key)

    with pytest.raises(AssertionError, match="live GitHub call in a test"):
        await create(client, config)
