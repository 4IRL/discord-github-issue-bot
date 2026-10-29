import dataclasses
import tomllib
from collections.abc import Mapping
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa

from issue_bot.config import (
    MAX_QUESTIONS,
    ROUTE_KEYS,
    Config,
    ConfigError,
    ProjectConfig,
    Question,
    QuestionStyle,
    TargetConfig,
    UnroutedCommands,
    _route_project,
    _route_questions,
    load_routes,
)
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
REPO_ROOT = Path(__file__).resolve().parent.parent
# The questions ONE_ROUTE_TOML defines, for literals compared with a loaded route.
ONE_ROUTE_QUESTIONS = {
    IssueType.BUG: (
        Question("What happened?", QuestionStyle.PARAGRAPH, True),
        Question("Device", QuestionStyle.SHORT, False),
    ),
    IssueType.FEATURE: (Question("The idea", QuestionStyle.PARAGRAPH, True),),
}


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
        questions=ONE_ROUTE_QUESTIONS,
        project=None,
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


def make_target(
    labels: dict[IssueType, str],
    questions: Mapping[IssueType, tuple[Question, ...]] = ONE_ROUTE_QUESTIONS,
) -> TargetConfig:
    return TargetConfig(
        name="intake",
        channel_id=555,
        channel_name="intake",
        category="Intake",
        github_repo="example-org/example-repo",
        github_repo_id=222,
        labels=labels,
        questions=questions,
        project=None,
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


def test_direct_construction_rejects_bad_project() -> None:
    with pytest.raises(ConfigError) as excinfo:
        dataclasses.replace(
            make_target({IssueType.BUG: "bug", IssueType.FEATURE: "enhancement"}),
            project="x",  # type: ignore[arg-type]
        )
    assert str(excinfo.value) == "project must be a ProjectConfig or None"


ORG = "example-org"
READABLE_ERROR = "ROUTES_PATH must name a readable TOML route file"
NO_ROUTES_ERROR = "ROUTES_PATH must define at least one [routes.<name>] table"
NAME_ERROR = "route names must be lowercase letters, digits, - or _"
LABELS_ERROR = "routes.intake.labels must map bug and feature to label names"
ONE_ROUTE_LINES = ONE_ROUTE_TOML.splitlines()
LABELS_HEADER = "[routes.intake.labels]"
# File-key order of the route's scalar keys and labels; cutting at the [routes.intake.labels]
# header also drops the question arrays after it. "questions" is left out: its arrays have no
# single line to drop, so without_questions covers it.
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
    """ONE_ROUTE_TOML with the named route keys removed.

    Dropping ``labels`` cuts at its header, which also drops the question arrays that follow it.
    """
    lines = list(ONE_ROUTE_LINES)
    if "labels" in keys:
        lines = lines[: lines.index(LABELS_HEADER)]
    lines = [line for line in lines if line.split(" = ")[0] not in keys]
    return "\n".join(lines) + "\n"


def without_questions(text: str) -> str:
    """``text`` cut at its first ``[[routes.intake.questions.`` header."""
    return text[: text.index("[[routes.intake.questions.")]


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
            questions=ONE_ROUTE_QUESTIONS,
            project=None,
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


PROJECT_LINES = {
    "number": "number = 2",
    "status_field": 'status_field = "Status"',
    "status": 'status = "Todo"',
    "effort_field": 'effort_field = "Effort"',
}
PROJECT_KEYS_IN_ORDER = list(PROJECT_LINES)
NUMBER_ERROR = "routes.intake.project.number must be a positive integer"


def with_project(**overrides: str | None) -> str:
    """ONE_ROUTE_TOML plus a ``[routes.intake.project]`` table.

    Each override replaces that key's line with ``key = value``; ``None`` drops the key.
    """
    lines = []
    for key, line in PROJECT_LINES.items():
        if key in overrides:
            if overrides[key] is None:
                continue
            line = f"{key} = {overrides[key]}"
        lines.append(line)
    return ONE_ROUTE_TOML + "\n[routes.intake.project]\n" + "\n".join(lines) + "\n"


def test_route_with_project_loads(tmp_path: Path) -> None:
    routes = load_text(tmp_path, with_project())
    assert routes[555].project == ProjectConfig(
        number=2, status_field="Status", status="Todo", effort_field="Effort"
    )


TRACK_FIELD_LINE = 'track_field = "Track"\n'
TRACK_DEFAULT_HEADER = "[routes.intake.project.track_default]\n"
TRACK_DEFAULT_ERROR = (
    "routes.intake.project.track_default must map bug or feature to Track option names"
)


def test_route_with_track_keys_loads(tmp_path: Path) -> None:
    text = with_project() + TRACK_FIELD_LINE + TRACK_DEFAULT_HEADER + 'bug = "A · Bugs"\n'
    assert load_text(tmp_path, text)[555].project == ProjectConfig(
        number=2,
        status_field="Status",
        status="Todo",
        effort_field="Effort",
        track_field="Track",
        track_defaults=((IssueType.BUG, "A · Bugs"),),
    )


def test_route_without_track_keys_has_no_track(tmp_path: Path) -> None:
    project = load_text(tmp_path, with_project())[555].project
    assert project is not None
    assert project.track_field is None
    assert project.track_defaults == ()


def test_track_defaults_load_in_issue_type_order_and_stripped(tmp_path: Path) -> None:
    text = (
        with_project()
        + TRACK_FIELD_LINE
        + TRACK_DEFAULT_HEADER
        + 'feature = "B · Form & feedback"\nbug = " A · Bugs "\n'
    )
    project = load_text(tmp_path, text)[555].project
    assert project is not None
    assert project.track_defaults == (
        (IssueType.BUG, "A · Bugs"),
        (IssueType.FEATURE, "B · Form & feedback"),
    )


def test_project_with_track_defaults_is_hashable(tmp_path: Path) -> None:
    text = with_project() + TRACK_FIELD_LINE + TRACK_DEFAULT_HEADER + 'bug = "A · Bugs"\n'
    project = load_text(tmp_path, text)[555].project
    assert project is not None
    assert hash(project) == hash(dataclasses.replace(project))


def test_route_without_project_loads(tmp_path: Path) -> None:
    assert load_text(tmp_path, ONE_ROUTE_TOML)[555].project is None


@pytest.mark.parametrize(
    ("text", "message"),
    [
        (
            ONE_ROUTE_TOML.replace("[routes.intake]\n", "[routes.intake]\nproject = 3\n"),
            "routes.intake.project must be a table",
        ),
        (
            with_project() + 'owner = "x"\n',
            "routes.intake.project has unknown key 'owner'",
        ),
        *[
            (with_project(**{key: None}), f"routes.intake.project.{key} is required")
            for key in PROJECT_KEYS_IN_ORDER
        ],
        *[
            (with_project(number=value), NUMBER_ERROR)
            for value in ["0", '"2"', "true"]
        ],
        *[
            (with_project(**{key: '"  "'}), f"routes.intake.project.{key} is required")
            for key in ["status_field", "status", "effort_field"]
        ],
        *[
            (with_project(**{key: "5"}), f"routes.intake.project.{key} must be a string")
            for key in ["status_field", "status", "effort_field"]
        ],
        (
            with_project() + 'track_field = ""\n',
            "routes.intake.project.track_field is required",
        ),
        (
            with_project() + "track_field = 3\n",
            "routes.intake.project.track_field must be a string",
        ),
        (
            with_project() + TRACK_DEFAULT_HEADER + 'bug = "A · Bugs"\n',
            "routes.intake.project.track_default needs track_field",
        ),
        *[
            (with_project() + TRACK_FIELD_LINE + f"track_default = {value}\n", TRACK_DEFAULT_ERROR)
            for value in [
                '"x"',
                '{chore = "x"}',
                '{bug = ""}',
                '{bug = "  "}',
                "{bug = 3}",
                "{}",
            ]
        ],
    ],
)
def test_project_errors(tmp_path: Path, text: str, message: str) -> None:
    assert route_error(tmp_path, text) == message


def test_project_error_does_not_quote_value(tmp_path: Path) -> None:
    error = route_error(tmp_path, with_project(status='["Secret words"]'))
    assert error == "routes.intake.project.status must be a string"
    assert "Secret words" not in error
    error = route_error(
        tmp_path, with_project() + TRACK_FIELD_LINE + 'track_default = {bug = ["Secret words"]}\n'
    )
    assert error == TRACK_DEFAULT_ERROR
    assert "Secret words" not in error


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
        ONE_ROUTE_TOML.replace(
            'feature = "enhancement"', 'feature = "enhancement"\ndocs = "documentation"'
        ),
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


QUESTIONS_MAP_ERROR = "routes.intake.questions must map bug and feature to question lists"
FEATURE_INLINE = '[{ label = "The idea", style = "paragraph", required = true }]'
FEATURE_TABLE = """
[[routes.intake.questions.feature]]
label = "The idea"
style = "paragraph"
required = true
"""


def with_inline_questions(value: str) -> str:
    """ONE_ROUTE_TOML with its question arrays replaced by ``questions = value`` in the route."""
    return without_questions(ONE_ROUTE_TOML).replace(
        "[routes.intake]\n", f"[routes.intake]\nquestions = {value}\n"
    )


def extra_bug_questions(labels: list[str]) -> str:
    """ONE_ROUTE_TOML plus one paragraph bug question per label, appended after its arrays."""
    tables = "".join(
        f'\n[[routes.intake.questions.bug]]\nlabel = "{label}"\nstyle = "paragraph"\n'
        "required = true\n"
        for label in labels
    )
    return ONE_ROUTE_TOML + tables


def test_route_questions_load(tmp_path: Path) -> None:
    route = load_text(tmp_path, ONE_ROUTE_TOML)[555]
    assert route.questions[IssueType.BUG] == (
        Question("What happened?", QuestionStyle.PARAGRAPH, True),
        Question("Device", QuestionStyle.SHORT, False),
    )
    assert route.questions[IssueType.BUG][1].style is QuestionStyle.SHORT
    assert route.questions[IssueType.FEATURE] == (
        Question("The idea", QuestionStyle.PARAGRAPH, True),
    )


def test_second_route_has_its_own_questions(tmp_path: Path) -> None:
    routes = load_text(tmp_path, TWO_ROUTE_TOML)
    assert routes[556].questions[IssueType.BUG] == (
        Question("Steps", QuestionStyle.PARAGRAPH, True),
    )
    assert routes[556].questions[IssueType.FEATURE] == (
        Question("Why?", QuestionStyle.SHORT, False),
    )


def test_route_questions_read_only(tmp_path: Path) -> None:
    route = load_text(tmp_path, ONE_ROUTE_TOML)[555]
    with pytest.raises(TypeError):
        route.questions[IssueType.BUG] = ()  # type: ignore[index]


def test_direct_construction_makes_questions_read_only() -> None:
    questions = dict(ONE_ROUTE_QUESTIONS)
    target = make_target({IssueType.BUG: "bug", IssueType.FEATURE: "enhancement"}, questions)
    questions[IssueType.BUG] = (Question("Changed", QuestionStyle.SHORT, False),)
    assert target.questions[IssueType.BUG] == ONE_ROUTE_QUESTIONS[IssueType.BUG]
    with pytest.raises(TypeError):
        target.questions[IssueType.BUG] = ()  # type: ignore[index]


@pytest.mark.parametrize(
    "questions",
    [
        {IssueType.BUG: ONE_ROUTE_QUESTIONS[IssueType.BUG]},
        {**ONE_ROUTE_QUESTIONS, "extra": ONE_ROUTE_QUESTIONS[IssueType.BUG]},
        {**ONE_ROUTE_QUESTIONS, IssueType.BUG: ()},
        {**ONE_ROUTE_QUESTIONS, IssueType.BUG: ONE_ROUTE_QUESTIONS[IssueType.FEATURE] * 5},
        {**ONE_ROUTE_QUESTIONS, IssueType.BUG: list(ONE_ROUTE_QUESTIONS[IssueType.BUG])},
        {**ONE_ROUTE_QUESTIONS, IssueType.BUG: ("What happened?",)},
        list(ONE_ROUTE_QUESTIONS),
    ],
    ids=[
        "missing-type",
        "extra-type",
        "empty",
        "too-many",
        "not-a-tuple",
        "not-a-question",
        "list",
    ],
)
def test_direct_construction_rejects_bad_questions(questions: object) -> None:
    labels = {IssueType.BUG: "bug", IssueType.FEATURE: "enhancement"}
    with pytest.raises(ConfigError) as excinfo:
        make_target(labels, questions)  # type: ignore[arg-type]
    assert str(excinfo.value) == "questions must have one entry per IssueType"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (without_questions(ONE_ROUTE_TOML), "routes.intake.questions is required"),
        (
            ONE_ROUTE_TOML.replace(FEATURE_TABLE, ""),
            QUESTIONS_MAP_ERROR,
        ),
        (
            ONE_ROUTE_TOML
            + '\n[[routes.intake.questions.docs]]\nlabel = "Page"\nstyle = "short"\n'
            "required = true\n",
            QUESTIONS_MAP_ERROR,
        ),
        (with_inline_questions("1"), QUESTIONS_MAP_ERROR),
        (with_inline_questions('{ bug = "x", feature = "y" }'), QUESTIONS_MAP_ERROR),
        (
            with_inline_questions(f"{{ bug = [], feature = {FEATURE_INLINE} }}"),
            "routes.intake.questions.bug must have 1 to 4 questions",
        ),
        (
            extra_bug_questions(["Expected", "Actual", "Browser"]),
            "routes.intake.questions.bug must have 1 to 4 questions",
        ),
        (
            with_inline_questions(f'{{ bug = ["x"], feature = {FEATURE_INLINE} }}'),
            "routes.intake.questions.bug[1] must be a table",
        ),
        (
            ONE_ROUTE_TOML + 'hint = "Say more"\n',
            "routes.intake.questions.feature[1] has unknown key 'hint'",
        ),
        (
            ONE_ROUTE_TOML.replace('label = "Device"\n', ""),
            "routes.intake.questions.bug[2].label is required",
        ),
        (
            ONE_ROUTE_TOML.replace('label = "Device"', 'label = "  "'),
            "routes.intake.questions.bug[2].label is required",
        ),
        (
            ONE_ROUTE_TOML.replace('label = "Device"', "label = 5"),
            "routes.intake.questions.bug[2].label must be a string",
        ),
        (
            ONE_ROUTE_TOML.replace('label = "Device"', f'label = "{"x" * 46}"'),
            "routes.intake.questions.bug[2].label must be at most 45 characters",
        ),
        (
            ONE_ROUTE_TOML.replace('style = "short"\n', ""),
            "routes.intake.questions.bug[2].style is required",
        ),
        (
            ONE_ROUTE_TOML.replace('style = "short"', 'style = "long"'),
            "routes.intake.questions.bug[2].style must be short or paragraph",
        ),
        (
            ONE_ROUTE_TOML.replace("required = false\n", ""),
            "routes.intake.questions.bug[2].required is required",
        ),
        (
            ONE_ROUTE_TOML.replace("required = false", "required = 1"),
            "routes.intake.questions.bug[2].required must be true or false",
        ),
        (
            ONE_ROUTE_TOML.replace("required = false", 'required = "yes"'),
            "routes.intake.questions.bug[2].required must be true or false",
        ),
        (
            ONE_ROUTE_TOML.replace('label = "Device"', 'label = "What happened?"'),
            "routes.intake.questions.bug labels must be unique",
        ),
    ],
    ids=[
        "missing-questions",
        "missing-type",
        "extra-type",
        "not-a-table",
        "type-not-an-array",
        "zero-questions",
        "five-questions",
        "question-not-a-table",
        "unknown-key",
        "missing-label",
        "blank-label",
        "non-string-label",
        "label-too-long",
        "missing-style",
        "bad-style",
        "missing-required",
        "integer-required",
        "string-required",
        "duplicate-label",
    ],
)
def test_bad_route_questions_raise(tmp_path: Path, text: str, expected: str) -> None:
    assert route_error(tmp_path, text) == expected


def test_label_of_45_characters_loads(tmp_path: Path) -> None:
    text = ONE_ROUTE_TOML.replace('label = "Device"', f'label = "{"x" * 45}"')
    assert load_text(tmp_path, text)[555].questions[IssueType.BUG][1].label == "x" * 45


def test_padded_question_label_is_stripped(tmp_path: Path) -> None:
    text = ONE_ROUTE_TOML.replace('label = "Device"', f'label = " {"x" * 45} "')
    assert load_text(tmp_path, text)[555].questions[IssueType.BUG][1].label == "x" * 45


def test_same_label_in_both_types_loads(tmp_path: Path) -> None:
    text = ONE_ROUTE_TOML.replace('label = "The idea"', 'label = "What happened?"')
    route = load_text(tmp_path, text)[555]
    assert route.questions[IssueType.FEATURE][0].label == "What happened?"


@pytest.mark.parametrize(
    "text",
    [
        ONE_ROUTE_TOML.replace('label = "Device"', f'label = "Secret words {"x" * 40}"'),
        ONE_ROUTE_TOML.replace('label = "Device"', 'label = "Secret words"').replace(
            'label = "What happened?"', 'label = "Secret words"'
        ),
    ],
    ids=["label-too-long", "duplicate-label"],
)
def test_question_errors_do_not_quote_labels(tmp_path: Path, text: str) -> None:
    assert "Secret words" not in route_error(tmp_path, text)


def test_example_env_lists_every_key() -> None:
    lines = (REPO_ROOT / "example.env").read_text().splitlines()
    entries = [line for line in lines if line.strip() and not line.lstrip().startswith("#")]
    assert all("=" in entry for entry in entries)
    keys = [entry.split("=", 1)[0].strip() for entry in entries]
    assert len(keys) == len(set(keys))
    assert set(keys) == set(ALL_KEYS)


def test_example_routes_shape() -> None:
    # Not loaded through load_routes: the example's placeholder ids are 0 by design.
    with open(REPO_ROOT / "example.routes.toml", "rb") as file:
        data = tomllib.load(file)
    routes = data["routes"]
    assert isinstance(routes, dict)
    assert routes
    for name, route in routes.items():
        assert set(route) == set(ROUTE_KEYS)
        assert set(route["labels"]) == {t.value for t in IssueType}
        assert set(route["questions"]) == {t.value for t in IssueType}
        for questions in route["questions"].values():
            assert 1 <= len(questions) <= MAX_QUESTIONS
        # The real validator checks every example question's keys, style and label length.
        _route_questions(route, f"routes.{name}")
        project = _route_project(route, f"routes.{name}")
        if name == "c4i":
            assert project is not None
