"""Session plan/close-out parser tests — focus on the regex fallback (no network needed)."""
from services.session_parser import SessionParser


def _force_fallback(monkeypatch):
    """Make the LLM path raise so we exercise the heuristic fallback."""
    from llm import groq_client

    def boom(*a, **k):
        raise groq_client.LLMUnavailable("forced")

    monkeypatch.setattr("services.session_parser.extract_json", boom)


def test_fallback_plan_extracts_duration_hours(monkeypatch):
    _force_fallback(monkeypatch)
    out = SessionParser().parse_plan("studying DSA for 3 hours")
    assert out["planned_duration_minutes"] == 180
    assert out["task_type"] == "unknown"
    assert "studying DSA" in out["title"] or out["title"]


def test_fallback_plan_extracts_duration_minutes(monkeypatch):
    _force_fallback(monkeypatch)
    out = SessionParser().parse_plan("quick email cleanup for 45 minutes")
    assert out["planned_duration_minutes"] == 45


def test_fallback_plan_combined_hours_and_minutes(monkeypatch):
    _force_fallback(monkeypatch)
    out = SessionParser().parse_plan("1 hour 30 minutes on the report")
    assert out["planned_duration_minutes"] == 90


def test_fallback_plan_defaults_when_no_duration_found(monkeypatch):
    _force_fallback(monkeypatch)
    out = SessionParser().parse_plan("write the report")
    assert out["planned_duration_minutes"] == 60


def test_fallback_closeout_not_done(monkeypatch):
    _force_fallback(monkeypatch)
    out = SessionParser().parse_closeout(
        "didn't touch it, ended up scrolling reddit instead", "write report", 60
    )
    assert out["completed"] is False
    assert out["displacement_type"] == "entertainment_escape"


def test_fallback_closeout_completed(monkeypatch):
    _force_fallback(monkeypatch)
    out = SessionParser().parse_closeout("done, finished it a bit late", "write report", 60)
    assert out["completed"] is True


def test_fallback_closeout_always_returns_full_shape(monkeypatch):
    _force_fallback(monkeypatch)
    out = SessionParser().parse_closeout("", "plan", 60)
    for key in [
        "completed", "outcome_hint", "actual_delay_minutes", "displacement_type",
        "reason", "unlock_trigger", "energy_level", "stress_level",
    ]:
        assert key in out
