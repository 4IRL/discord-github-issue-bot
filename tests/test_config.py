import dataclasses
from collections.abc import Mapping
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa

from issue_bot.config import Config, ConfigError, TargetConfig, UnroutedCommands, load_routes
from issue_bot.issue_type import IssueType
from tests.conftest import ONE_ROUTE_TOML, TWO_ROUTE_TOML, write_routes

ALL_KEYS = [
    "DISCORD_TOKEN",
    "DISCORD_GUILD_ID",
    "UNROUTED_COMMANDS",
    "GITHUB_ORG",
    "GITHUB_APP_ID",
    "GITHUB_APP_INSTALLATION_ID",
    "GITHUB_APP_PRIVATE_KEY_PATH",
    "ROUTES_PATH",
]
ID_KEYS = ["DISCORD_GUILD_ID", "GITHUB_APP_ID", "GITHUB_APP_INSTALLATION_ID"]
PRIVATE_KEY_ERROR = "GITHUB_APP_PRIVATE_KEY_PATH must name a readable RSA private key"


def test_full_env_loads(test_env: dict[str, str]) -> None:
    config = Config.from_env(test_env)
    assert config.guild_id == 111
    assert config.unrouted is UnroutedCommands.REFUSE
    assert config.github_org == "example-org"
    assert config.github_app_id == 333
    assert config.github_installation_id == 444
    assert isinstance(config.github_private_key, rsa.RSAPrivateKey)
    assert list(config.routes) == [555]
    assert config.routes[555] == TargetConfig(
        name="intake",
        channel_id=555,
        channel_name="intake",
        category="Intake",
        github_repo="example-org/example-repo",
        github_repo_id=222,
        labels={IssueType.BUG: "bug", IssueType.FEATURE: "enhancement"},
    )


@pytest.mark.parametrize("key", ALL_KEYS)
def test_each_key_required(test_env: dict[str, str], key: str) -> None:
    del test_env[key]
    with pytest.raises(ConfigError) as excinfo:
        Config.from_env(test_env)
    assert str(excinfo.value) == f"{key} is required"


@pytest.mark.parametrize("position", range(len(ALL_KEYS)))
def test_first_missing_key_in_order_is_reported(
    test_env: dict[str, str], position: int
) -> None:
    for later_key in ALL_KEYS[position:]:
        del test_env[later_key]
    with pytest.raises(ConfigError) as excinfo:
        Config.from_env(test_env)
    assert str(excinfo.value) == f"{ALL_KEYS[position]} is required"


def test_blank_value_counts_as_missing(test_env: dict[str, str]) -> None:
    test_env["GITHUB_ORG"] = "  "
    with pytest.raises(ConfigError) as excinfo:
        Config.from_env(test_env)
    assert str(excinfo.value) == "GITHUB_ORG is required"


@pytest.mark.parametrize("value", ["abc", "١٢٣", "+5", "1_000", "9" * 5000])
@pytest.mark.parametrize("key", ID_KEYS)
def test_non_integer_id_raises(test_env: dict[str, str], key: str, value: str) -> None:
    test_env[key] = value
    with pytest.raises(ConfigError) as excinfo:
        Config.from_env(test_env)
    assert str(excinfo.value) == f"{key} must be an integer"


def test_padded_id_is_stripped(test_env: dict[str, str]) -> None:
    test_env["DISCORD_GUILD_ID"] = " 111 "
    config = Config.from_env(test_env)
    assert config.guild_id == 111


@pytest.mark.parametrize("value", ["0", "-5"])
@pytest.mark.parametrize("key", ID_KEYS)
def test_non_positive_id_raises(test_env: dict[str, str], key: str, value: str) -> None:
    test_env[key] = value
    with pytest.raises(ConfigError) as excinfo:
        Config.from_env(test_env)
    assert str(excinfo.value) == f"{key} must be a positive integer"


@pytest.mark.parametrize("value", ["silent", "Refuse"])
def test_bad_unrouted_commands_raises(test_env: dict[str, str], value: str) -> None:
    test_env["UNROUTED_COMMANDS"] = value
    with pytest.raises(ConfigError) as excinfo:
        Config.from_env(test_env)
    assert str(excinfo.value) == "UNROUTED_COMMANDS must be refuse or ignore"


def test_padded_unrouted_commands_loads(test_env: dict[str, str]) -> None:
    test_env["UNROUTED_COMMANDS"] = " ignore "
    assert Config.from_env(test_env).unrouted is UnroutedCommands.IGNORE


@pytest.mark.parametrize("value", ["a/b", ".."])
def test_bad_github_org_raises(test_env: dict[str, str], value: str) -> None:
    test_env["GITHUB_ORG"] = value
    with pytest.raises(ConfigError) as excinfo:
        Config.from_env(test_env)
    assert str(excinfo.value) == "GITHUB_ORG must be an owner name"


def test_route_repo_outside_github_org_raises(test_env: dict[str, str], tmp_path: Path) -> None:
    path = write_routes(
        tmp_path / "foreign",
        ONE_ROUTE_TOML.replace("example-org/example-repo", "other-org/example-repo"),
    )
    test_env["ROUTES_PATH"] = str(path)
    with pytest.raises(ConfigError) as excinfo:
        Config.from_env(test_env)
    assert str(excinfo.value) == "routes.intake.repo must be in GITHUB_ORG"


def test_config_routes_read_only(config: Config, route: TargetConfig) -> None:
    with pytest.raises(TypeError):
        config.routes[556] = route  # type: ignore[index]


def test_direct_construction_makes_routes_read_only(config: Config, route: TargetConfig) -> None:
    routes = {555: route}
    direct = dataclasses.replace(config, routes=routes)
    routes[556] = route
    assert list(direct.routes) == [555]
    with pytest.raises(TypeError):
        direct.routes[556] = route  # type: ignore[index]


def test_token_not_in_repr(test_env: dict[str, str]) -> None:
    test_env["DISCORD_TOKEN"] = "secret-value"
    config = Config.from_env(test_env)
    assert "secret-value" not in repr(config)


def test_private_key_not_in_repr(
    test_env: dict[str, str], github_private_key_pem: Path
) -> None:
    config = Config.from_env(test_env)
    config_repr = repr(config)
    pem_body_line = github_private_key_pem.read_text().splitlines()[1]
    assert "github_private_key" not in config_repr
    assert "PrivateKey" not in config_repr
    assert pem_body_line not in config_repr


def load_with_key_file(
    test_env: dict[str, str], key_path: Path
) -> pytest.ExceptionInfo[ConfigError]:
    """Point the key path at ``key_path`` and assert loading fails with the fixed message."""
    test_env["GITHUB_APP_PRIVATE_KEY_PATH"] = str(key_path)
    with pytest.raises(ConfigError) as excinfo:
        Config.from_env(test_env)
    assert str(excinfo.value) == PRIVATE_KEY_ERROR
    return excinfo


def test_private_key_path_missing_raises(test_env: dict[str, str], tmp_path: Path) -> None:
    load_with_key_file(test_env, tmp_path / "missing-key.txt")


def test_private_key_path_is_directory_raises(
    test_env: dict[str, str], tmp_path: Path
) -> None:
    load_with_key_file(test_env, tmp_path)


def test_private_key_empty_file_raises(test_env: dict[str, str], tmp_path: Path) -> None:
    key_path = tmp_path / "empty-key.txt"
    key_path.write_bytes(b"")
    load_with_key_file(test_env, key_path)


def test_private_key_not_pem_raises(test_env: dict[str, str], tmp_path: Path) -> None:
    key_path = tmp_path / "not-a-key.txt"
    key_path.write_text("Secret key words")
    excinfo = load_with_key_file(test_env, key_path)
    assert "Secret key words" not in str(excinfo.value)


def test_private_key_not_rsa_raises(test_env: dict[str, str], tmp_path: Path) -> None:
    key_path = tmp_path / "ec-key.txt"
    key_path.write_bytes(
        ec.generate_private_key(ec.SECP256R1()).private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    load_with_key_file(test_env, key_path)


def test_private_key_error_hides_path(test_env: dict[str, str], tmp_path: Path) -> None:
    key_path = tmp_path / "missing-key.txt"
    excinfo = load_with_key_file(test_env, key_path)
    assert str(key_path) not in str(excinfo.value)


def test_private_key_encrypted_raises(
    test_env: dict[str, str], tmp_path: Path, github_private_key: rsa.RSAPrivateKey
) -> None:
    key_path = tmp_path / "encrypted-key.txt"
    key_path.write_bytes(
        github_private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.BestAvailableEncryption(b"pw"),
        )
    )
    load_with_key_file(test_env, key_path)


def test_labels_read_only(route: TargetConfig) -> None:
    with pytest.raises(TypeError):
        route.labels[IssueType.BUG] = "x"  # type: ignore[index]


def make_target(labels: dict[IssueType, str]) -> TargetConfig:
    return TargetConfig(
        name="intake",
        channel_id=555,
        channel_name="intake",
        category="Intake",
        github_repo="example-org/example-repo",
        github_repo_id=222,
        labels=labels,
    )


@pytest.mark.parametrize(
    "labels",
    [
        {IssueType.BUG: "bug"},
        {IssueType.BUG: "bug", IssueType.FEATURE: "enhancement", "extra": "x"},
        [IssueType.BUG, IssueType.FEATURE],
    ],
)
def test_direct_construction_rejects_bad_labels(labels: object) -> None:
    with pytest.raises(ConfigError) as excinfo:
        make_target(labels)  # type: ignore[arg-type]
    assert str(excinfo.value) == "labels must have one entry per IssueType"


def test_direct_construction_makes_labels_read_only() -> None:
    labels = {IssueType.BUG: "bug", IssueType.FEATURE: "enhancement"}
    target = make_target(labels)
    labels[IssueType.BUG] = "changed"
    assert target.labels[IssueType.BUG] == "bug"
    with pytest.raises(TypeError):
        target.labels[IssueType.BUG] = "x"  # type: ignore[index]


ORG = "example-org"
READABLE_ERROR = "ROUTES_PATH must name a readable TOML route file"
NO_ROUTES_ERROR = "ROUTES_PATH must define at least one [routes.<name>] table"
NAME_ERROR = "route names must be lowercase letters, digits, - or _"
LABELS_ERROR = "routes.intake.labels must map bug and feature to label names"
ONE_ROUTE_LINES = ONE_ROUTE_TOML.splitlines()
LABELS_HEADER = "[routes.intake.labels]"
# File-key order of the route's keys; "labels" is the trailing [routes.intake.labels] table.
ROUTE_FILE_KEYS = ["channel_id", "channel_name", "category", "repo", "repo_id", "labels"]


def load_text(tmp_path: Path, text: str) -> Mapping[int, TargetConfig]:
    return load_routes(str(write_routes(tmp_path, text)), ORG)


def route_error(tmp_path: Path, text: str) -> str:
    with pytest.raises(ConfigError) as excinfo:
        load_text(tmp_path, text)
    return str(excinfo.value)


def with_route_line(key: str, value: str) -> str:
    """ONE_ROUTE_TOML with ``key``'s line replaced by ``key = value``."""
    prefix = f"{key} = "
    assert sum(line.startswith(prefix) for line in ONE_ROUTE_LINES) == 1
    lines = [prefix + value if line.startswith(prefix) else line for line in ONE_ROUTE_LINES]
    return "\n".join(lines) + "\n"


def without_route_keys(keys: list[str]) -> str:
    """ONE_ROUTE_TOML with the named route keys removed (``labels`` drops its whole table)."""
    lines = list(ONE_ROUTE_LINES)
    if "labels" in keys:
        lines = lines[: lines.index(LABELS_HEADER)]
    lines = [line for line in lines if line.split(" = ")[0] not in keys]
    return "\n".join(lines) + "\n"


def test_one_route_loads(tmp_path: Path) -> None:
    routes = load_text(tmp_path, ONE_ROUTE_TOML)
    assert routes == {
        555: TargetConfig(
            name="intake",
            channel_id=555,
            channel_name="intake",
            category="Intake",
            github_repo="example-org/example-repo",
            github_repo_id=222,
            labels={IssueType.BUG: "bug", IssueType.FEATURE: "enhancement"},
        )
    }


def test_two_routes_load_in_file_order(tmp_path: Path) -> None:
    routes = load_text(tmp_path, TWO_ROUTE_TOML)
    assert list(routes) == [555, 556]
    assert routes[556].name == "other"
    assert routes[556].github_repo == "example-org/other-repo"
    assert routes[556].github_repo_id == 223
    assert dict(routes[556].labels) == {IssueType.BUG: "defect", IssueType.FEATURE: "idea"}


def test_routes_mapping_is_read_only(tmp_path: Path) -> None:
    routes = load_text(tmp_path, ONE_ROUTE_TOML)
    with pytest.raises(TypeError):
        routes[556] = routes[555]  # type: ignore[index]


def test_missing_route_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ConfigError) as excinfo:
        load_routes(str(tmp_path / "missing.toml"), ORG)
    assert str(excinfo.value) == READABLE_ERROR


def test_route_file_is_directory_raises(tmp_path: Path) -> None:
    with pytest.raises(ConfigError) as excinfo:
        load_routes(str(tmp_path), ORG)
    assert str(excinfo.value) == READABLE_ERROR


def test_malformed_toml_raises_without_quoting_file(tmp_path: Path) -> None:
    error = route_error(tmp_path, "[routes.intake]\nchannel_id = Secret words\n")
    assert error == READABLE_ERROR


def test_invalid_utf8_raises(tmp_path: Path) -> None:
    path = tmp_path / "routes.toml"
    path.write_bytes(b'[routes.intake]\nchannel_name = "\xff"\n')
    with pytest.raises(ConfigError) as excinfo:
        load_routes(str(path), ORG)
    assert str(excinfo.value) == READABLE_ERROR


@pytest.mark.parametrize("text", ["", "# no routes\n", "[routes]\n", "routes = 1\n"])
def test_no_routes_raises(tmp_path: Path, text: str) -> None:
    assert route_error(tmp_path, text) == NO_ROUTES_ERROR


def test_unknown_top_level_key_raises(tmp_path: Path) -> None:
    error = route_error(tmp_path, "extra = 1\n" + ONE_ROUTE_TOML)
    assert error == "ROUTES_PATH has unknown key 'extra'"


@pytest.mark.parametrize("header", ["[routes.Intake]", '[routes."a b"]'])
def test_bad_route_name_raises(tmp_path: Path, header: str) -> None:
    text = ONE_ROUTE_TOML.replace("[routes.intake]", header).replace(
        LABELS_HEADER, header[:-1] + ".labels]"
    )
    assert route_error(tmp_path, text) == NAME_ERROR


def test_non_table_route_raises(tmp_path: Path) -> None:
    assert route_error(tmp_path, "routes.intake = 1\n") == "routes.intake must be a table"


@pytest.mark.parametrize("key", ROUTE_FILE_KEYS)
def test_each_route_key_required(tmp_path: Path, key: str) -> None:
    assert route_error(tmp_path, without_route_keys([key])) == f"routes.intake.{key} is required"


@pytest.mark.parametrize("position", range(len(ROUTE_FILE_KEYS)))
def test_first_missing_route_key_in_order_is_reported(tmp_path: Path, position: int) -> None:
    text = without_route_keys(ROUTE_FILE_KEYS[position:])
    assert route_error(tmp_path, text) == f"routes.intake.{ROUTE_FILE_KEYS[position]} is required"


def test_unknown_route_key_raises(tmp_path: Path) -> None:
    text = ONE_ROUTE_TOML.replace("[routes.intake]\n", "[routes.intake]\nchanel_id = 1\n")
    assert route_error(tmp_path, text) == "routes.intake has unknown key 'chanel_id'"


@pytest.mark.parametrize("key", ["channel_id", "repo_id"])
@pytest.mark.parametrize("value", ["0", "-1", '"555"', "true", "1.5"])
def test_route_id_must_be_positive_integer(tmp_path: Path, key: str, value: str) -> None:
    error = route_error(tmp_path, with_route_line(key, value))
    assert error == f"routes.intake.{key} must be a positive integer"


@pytest.mark.parametrize("key", ["channel_name", "category", "repo"])
def test_blank_route_string_is_required(tmp_path: Path, key: str) -> None:
    assert route_error(tmp_path, with_route_line(key, '"  "')) == f"routes.intake.{key} is required"


@pytest.mark.parametrize("key", ["channel_name", "category", "repo"])
def test_route_string_must_be_string(tmp_path: Path, key: str) -> None:
    error = route_error(tmp_path, with_route_line(key, "5"))
    assert error == f"routes.intake.{key} must be a string"


def test_padded_route_strings_are_stripped(tmp_path: Path) -> None:
    text = (
        with_route_line("channel_name", '" intake "')
        .replace('category = "Intake"', 'category = " Intake "')
        .replace('repo = "example-org/example-repo"', 'repo = " example-org/example-repo "')
        .replace('bug = "bug"', 'bug = " bug "')
    )
    route = load_text(tmp_path, text)[555]
    assert route.channel_name == "intake"
    assert route.category == "Intake"
    assert route.github_repo == "example-org/example-repo"
    assert route.labels[IssueType.BUG] == "bug"


@pytest.mark.parametrize("repo", ['"example-org"', '"a/b/c"', '"example-org/.."'])
def test_bad_route_repo_format(tmp_path: Path, repo: str) -> None:
    error = route_error(tmp_path, with_route_line("repo", repo))
    assert error == "routes.intake.repo must be owner/name"


def test_route_repo_outside_org_raises(tmp_path: Path) -> None:
    error = route_error(tmp_path, with_route_line("repo", '"other-org/example-repo"'))
    assert error == "routes.intake.repo must be in GITHUB_ORG"


def test_route_repo_owner_matches_org_case_insensitively(tmp_path: Path) -> None:
    routes = load_text(tmp_path, with_route_line("repo", '"EXAMPLE-ORG/example-repo"'))
    assert routes[555].github_repo == "EXAMPLE-ORG/example-repo"


@pytest.mark.parametrize(
    "text",
    [
        without_route_keys(["feature"]),
        ONE_ROUTE_TOML + 'docs = "documentation"\n',
        without_route_keys(["labels"]) + 'labels = "bug"\n',
        ONE_ROUTE_TOML.replace('feature = "enhancement"', 'feature = "  "'),
        ONE_ROUTE_TOML.replace('feature = "enhancement"', "feature = 5"),
    ],
    ids=["missing-feature", "extra-docs", "not-a-table", "blank-value", "non-string-value"],
)
def test_bad_route_labels_raise(tmp_path: Path, text: str) -> None:
    assert route_error(tmp_path, text) == LABELS_ERROR


def test_duplicate_channel_id_raises(tmp_path: Path) -> None:
    text = TWO_ROUTE_TOML.replace("channel_id = 556", "channel_id = 555")
    assert route_error(tmp_path, text) == "routes.intake and routes.other share channel_id"
