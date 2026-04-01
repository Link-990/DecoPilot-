"""
????ID?????
"""
from file_history_store import sanitize_session_id


def test_sanitize_session_id_basic():
    assert sanitize_session_id("") == "session"
    assert sanitize_session_id(None) == "session"


def test_sanitize_session_id_removes_separators():
    unsafe = "../etc/passwd"
    safe = sanitize_session_id(unsafe)
    assert "/" not in safe
    assert "\\" not in safe
