"""Check-in parser tests — focus on the regex fallback (no network needed)."""
from services.checkin_parser import CheckinParser


def _force_fallback(monkeypatch):
    """Make the LLM path raise so we exercise the heuristic fallback."""
    from llm import groq_client

    def boom(*a, **k):
        raise groq_client.LLMUnavailable("forced")

    monkeypatch.setattr("services.checkin_parser.extract_json", boom)


def test_fallback_extracts_energy_and_meetings(monkeypatch):
    _force_fallback(monkeypatch)
    parser = CheckinParser()
    out = parser.parse(
        "had three back-to-back calls this morning, exhausted 2/5, kept opening twitter"
    )
    assert out["energy_level"] == 2
    assert out["had_heavy_meetings"] is True
    assert out["social_context"] == "just_had_meeting"
    assert out["emotional_texture"] == "fatigue"
    assert out["sentiment"] == "negative"


def test_fallback_scale_out_of_ten(monkeypatch):
    _force_fallback(monkeypatch)
    out = CheckinParser().parse("energy is like 8/10 today, feeling good, finished the report")
    assert out["energy_level"] == 4  # 8/10 normalized to /5
    assert out["sentiment"] == "positive"


def test_fallback_sleep_hours(monkeypatch):
    _force_fallback(monkeypatch)
    out = CheckinParser().parse("only got 5 hours of sleep and I'm dragging")
    assert out["hours_of_sleep"] == 5.0


def test_fallback_always_returns_full_shape(monkeypatch):
    _force_fallback(monkeypatch)
    out = CheckinParser().parse("")
    for key in [
        "energy_level", "stress_level", "social_context", "hours_of_sleep",
        "emotional_texture", "tasks_mentioned", "sentiment",
    ]:
        assert key in out
    assert isinstance(out["tasks_mentioned"], list)


def test_match_tasks_to_ids(fresh_db, monkeypatch):
    db = fresh_db.get_db()
    db.execute(
        "INSERT INTO tasks (id, user_id, source, title, status) "
        "VALUES ('x1', 'u1', 'manual', 'Write the client proposal', 'pending')"
    )
    db.commit()
    matched = CheckinParser().match_tasks_to_ids(["client proposal"], "u1")
    assert matched == ["x1"]


def test_match_tasks_to_ids_scoped_to_user(fresh_db, monkeypatch):
    """A task belonging to another user must never match."""
    db = fresh_db.get_db()
    db.execute(
        "INSERT INTO tasks (id, user_id, source, title, status) "
        "VALUES ('x1', 'other-user', 'manual', 'Write the client proposal', 'pending')"
    )
    db.commit()
    matched = CheckinParser().match_tasks_to_ids(["client proposal"], "u1")
    assert matched == []
