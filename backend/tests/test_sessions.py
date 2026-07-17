"""Session lifecycle tests: start -> closeout, outcome computation, and the
lazy active -> pending_closeout state flip.

Route functions are called directly (FastAPI's @router.post/.get decorators
return the original function unchanged) so these run without an ASGI server,
using a lightweight fake user object in place of the auth dependency.
"""
from datetime import timedelta

from api import routes
from timeutil import now_ist, iso_ist


class FakeUser:
    def __init__(self, uid="test-user-1"):
        self.id = uid


def _force_fallback(monkeypatch):
    """No LLM in tests — exercise the deterministic regex fallback path."""
    from llm import groq_client

    def boom(*a, **k):
        raise groq_client.LLMUnavailable("forced")

    monkeypatch.setattr("services.session_parser.extract_json", boom)


def test_start_session_creates_active_row(fresh_db, monkeypatch):
    _force_fallback(monkeypatch)
    user = FakeUser()
    result = routes.start_session(routes.SessionStartInput(text="write report for 1 hour"), user)
    assert result["status"] == "active"
    assert result["planned_duration_minutes"] == 60
    assert result["outcome"] is None


def test_double_start_conflicts(fresh_db, monkeypatch):
    _force_fallback(monkeypatch)
    user = FakeUser()
    routes.start_session(routes.SessionStartInput(text="write report for 1 hour"), user)
    try:
        routes.start_session(routes.SessionStartInput(text="something else"), user)
        assert False, "expected HTTPException"
    except Exception as e:
        assert "409" in str(getattr(e, "status_code", "")) or getattr(e, "status_code", None) == 409


def test_closeout_before_planned_end_is_early(fresh_db, monkeypatch):
    _force_fallback(monkeypatch)
    user = FakeUser()
    session = routes.start_session(routes.SessionStartInput(text="write report for 3 hours"), user)
    result = routes.closeout_session(session["id"], routes.SessionCloseoutInput(text="finished early"), user)
    assert result["outcome"] == "early"
    assert result["delay_minutes"] == 0.0
    assert result["derived_event_id"] is None


def _start_and_backdate(db, user, text, hours_ago):
    """Start a session, then push planned_start/planned_end into the past so
    closing it out lands after planned_end (simulating elapsed time without
    actually sleeping in the test)."""
    session = routes.start_session(routes.SessionStartInput(text=text), user)
    db.execute(
        "UPDATE sessions SET planned_start = datetime(planned_start, ?), "
        "planned_end = datetime(planned_end, ?) WHERE id = ?",
        (f"-{hours_ago} hours", f"-{hours_ago} hours", session["id"]),
    )
    db.commit()
    return session["id"]


def test_closeout_completed_but_late_is_delayed(fresh_db, monkeypatch):
    _force_fallback(monkeypatch)
    from db.db import get_db
    user = FakeUser()
    db = get_db()
    sid = _start_and_backdate(db, user, "write report for 30 minutes", hours_ago=1)

    result = routes.closeout_session(
        sid, routes.SessionCloseoutInput(text="finished it, done"), user
    )
    assert result["outcome"] == "delayed"
    assert result["delay_minutes"] > 15
    assert result["derived_event_id"] is not None

    # the derived event carries the session's task_type and a sensible delay_hours
    ev = db.execute(
        "SELECT * FROM procrastination_events WHERE id = ?", (result["derived_event_id"],)
    ).fetchone()
    assert ev["detection_source"] == "session"
    assert ev["task_type"] == "unknown"
    assert ev["delay_hours"] > 0


def test_closeout_not_completed_is_not_done(fresh_db, monkeypatch):
    _force_fallback(monkeypatch)
    from db.db import get_db
    user = FakeUser()
    db = get_db()
    sid = _start_and_backdate(db, user, "write report for 30 minutes", hours_ago=1)

    result = routes.closeout_session(
        sid,
        routes.SessionCloseoutInput(text="didn't touch it, ended up doomscrolling instead"),
        user,
    )
    assert result["outcome"] == "not_done"
    assert result["derived_event_id"] is not None


def test_closeout_within_grace_window_is_on_time(fresh_db, monkeypatch):
    _force_fallback(monkeypatch)
    from db.db import get_db
    user = FakeUser()
    db = get_db()
    session = routes.start_session(routes.SessionStartInput(text="write report for 30 minutes"), user)
    # Move planned_start/planned_end back by 35 minutes so planned_end (30 min
    # after start) lands 5 minutes in the past — inside the 15-min grace window.
    db.execute(
        "UPDATE sessions SET planned_start = datetime(planned_start, '-35 minutes'), "
        "planned_end = datetime(planned_end, '-35 minutes') WHERE id = ?",
        (session["id"],),
    )
    db.commit()
    result = routes.closeout_session(
        session["id"], routes.SessionCloseoutInput(text="done, finished it"), user
    )
    assert result["outcome"] == "on_time"
    assert result["derived_event_id"] is None


def test_active_session_flips_to_pending_closeout(fresh_db, monkeypatch):
    _force_fallback(monkeypatch)
    from db.db import get_db
    user = FakeUser()
    db = get_db()
    sid = _start_and_backdate(db, user, "write report for 30 minutes", hours_ago=1)

    active = routes.get_active_session(user)
    assert active is not None
    assert active["id"] == sid
    assert active["status"] == "pending_closeout"


def test_no_active_session_returns_none(fresh_db, monkeypatch):
    _force_fallback(monkeypatch)
    user = FakeUser()
    assert routes.get_active_session(user) is None
