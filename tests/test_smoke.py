def test_package_imports() -> None:
    import issue_bot

    assert issue_bot.__name__ == "issue_bot"
