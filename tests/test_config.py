import pytest

from issue_bot.config import Config, ConfigError, TargetConfig
from issue_bot.tags import IssueType

ALL_KEYS = [
    "DISCORD_TOKEN",
    "DISCORD_GUILD_ID",
    "DISCORD_CHANNEL_ID",
    "DISCORD_CHANNEL_NAME",
    "DISCORD_CATEGORY",
    "GITHUB_REPO",
    "GITHUB_REPO_ID",
    "GITHUB_LABEL_BUG",
    "GITHUB_LABEL_FEATURE",
]
ID_KEYS = ["DISCORD_GUILD_ID", "DISCORD_CHANNEL_ID", "GITHUB_REPO_ID"]


def test_full_env_loads(test_env: dict[str, str]) -> None:
    config = Config.from_env(test_env)
    assert config.guild_id == 111
    assert isinstance(config.target, TargetConfig)
    assert config.target.channel_id == 555
    assert config.target.channel_name == "intake"
    assert config.target.category == "Intake"
    assert config.target.github_repo == "example-org/example-repo"
    assert config.target.github_repo_id == 222
    assert dict(config.target.labels) == {
        IssueType.BUG: "bug",
        IssueType.FEATURE: "enhancement",
    }


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
    test_env["DISCORD_CHANNEL_NAME"] = "  "
    with pytest.raises(ConfigError) as excinfo:
        Config.from_env(test_env)
    assert str(excinfo.value) == "DISCORD_CHANNEL_NAME is required"


@pytest.mark.parametrize("value", ["abc", "١٢٣", "+5", "1_000", "9" * 5000])
@pytest.mark.parametrize("key", ID_KEYS)
def test_non_integer_id_raises(test_env: dict[str, str], key: str, value: str) -> None:
    test_env[key] = value
    with pytest.raises(ConfigError) as excinfo:
        Config.from_env(test_env)
    assert str(excinfo.value) == f"{key} must be an integer"


def test_padded_id_is_stripped(test_env: dict[str, str]) -> None:
    test_env["DISCORD_CHANNEL_ID"] = " 555 "
    config = Config.from_env(test_env)
    assert config.target.channel_id == 555


@pytest.mark.parametrize("value", ["0", "-5"])
@pytest.mark.parametrize("key", ID_KEYS)
def test_non_positive_id_raises(test_env: dict[str, str], key: str, value: str) -> None:
    test_env[key] = value
    with pytest.raises(ConfigError) as excinfo:
        Config.from_env(test_env)
    assert str(excinfo.value) == f"{key} must be a positive integer"


@pytest.mark.parametrize(
    "repo", ["noslash", "a/b/c", "own er/repo", "../..", "./x", "a/..", "../x"]
)
def test_bad_repo_format(test_env: dict[str, str], repo: str) -> None:
    test_env["GITHUB_REPO"] = repo
    with pytest.raises(ConfigError) as excinfo:
        Config.from_env(test_env)
    assert str(excinfo.value) == "GITHUB_REPO must be owner/name"


def test_token_not_in_repr(test_env: dict[str, str]) -> None:
    test_env["DISCORD_TOKEN"] = "secret-value"
    config = Config.from_env(test_env)
    assert "secret-value" not in repr(config)


def test_labels_read_only(config: Config) -> None:
    with pytest.raises(TypeError):
        config.target.labels[IssueType.BUG] = "x"  # type: ignore[index]


def make_target(labels: dict[IssueType, str]) -> TargetConfig:
    return TargetConfig(
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
