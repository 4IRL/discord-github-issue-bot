"""Entry point: ``python -m issue_bot``."""

import logging
import os

from issue_bot.bot import IssueBot, filing_hook
from issue_bot.config import Config, ConfigError
from issue_bot.github import GitHubClient

logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    try:
        config = Config.from_env(os.environ)
    except ConfigError as exc:
        logger.error("configuration error: %s", exc)
        raise SystemExit(2) from None
    github = GitHubClient(
        config.github_app_id, config.github_installation_id, config.github_private_key
    )
    IssueBot(
        config, on_candidate=filing_hook(github), filing_check=github.check_access
    ).run(config.discord_token, log_handler=None)


if __name__ == "__main__":
    main()
