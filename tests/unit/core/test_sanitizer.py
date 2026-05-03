from kree.core.sanitizer import sanitize_command


def test_safe_command_passes_through():
    text, err = sanitize_command("open notepad")
    assert text == "open notepad"
    assert err is None


def test_blocked_command_returns_none_and_error():
    text, err = sanitize_command("rm -rf /home/user")
    assert text is None
    assert "rm -rf" in err


def test_blocked_command_case_insensitive():
    text, err = sanitize_command("DELETE SYSTEM32")
    assert text is None
    assert err is not None


def test_empty_string_passes_through():
    text, err = sanitize_command("")
    assert text == ""
    assert err is None


def test_none_like_empty_passes_through():
    text, err = sanitize_command("  notepad  ")
    assert text == "  notepad  "
    assert err is None
