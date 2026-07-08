"""Enricher + insight-generator tests (AW stubbed, no network)."""
import json
from datetime import datetime, timezone

from services.event_enricher import EventEnricher
from analysis.insight_generator import InsightGenerator, confidence_for
from db.db import generate_id

UID = "test-user-1"


def _task_and_open_event(db, user_id=UID):
    db.execute(
        "INSERT INTO tasks (id, user_id, source, title, task_type, created_at, status) "
        "VALUES ('t1', ?, 'manual','Write report','creative',?, 'pending')",
        (user_id, datetime.now(timezone.utc).isoformat()),
    )
    eid = generate_id()
    db.execute(
        """INSERT INTO procrastination_events (id, user_id, task_id, detected_at, delay_start_at, delay_hours)
           VALUES (?, ?, 't1', ?, ?, 6.0)""",
        (eid, user_id, "2026-06-01T10:00:00+00:00", "2026-06-01T08:00:00+00:00"),
    )
    db.commit()
    return eid


def test_enricher_noop_when_aw_unavailable(fresh_db, monkeypatch):
    db = fresh_db.get_db()
    eid = _task_and_open_event(db)
    monkeypatch.setattr(
        "services.event_enricher.ActivityFetcher.is_available", lambda self: False
    )
    assert EventEnricher(UID).enrich_pending_event(eid) is None


def test_enricher_writes_displacement(fresh_db, monkeypatch):
    db = fresh_db.get_db()
    eid = _task_and_open_event(db)

    monkeypatch.setattr(
        "services.event_enricher.ActivityFetcher.is_available", lambda self: True
    )
    fake = {
        "type": "entertainment_escape",
        "breakdown": {"entertainment_escape": 1.0},
        "total_minutes": 90.0,
        "windows": [{
            "started_at": "2026-06-01T08:30:00+00:00",
            "ended_at": "2026-06-01T10:00:00+00:00",
            "app_name": "YouTube", "window_title": "video", "category": "entertainment_escape",
            "duration_minutes": 90.0,
        }],
    }
    monkeypatch.setattr(
        "services.event_enricher.ActivityFetcher.get_displacement_during_delay",
        lambda self, s, e: fake,
    )

    out = EventEnricher(UID).enrich_pending_event(eid)
    assert out["type"] == "entertainment_escape"

    row = db.execute(
        "SELECT displacement_type, displacement_duration_minutes, detection_source "
        "FROM procrastination_events WHERE id = ?", (eid,)
    ).fetchone()
    assert row["displacement_type"] == "entertainment_escape"
    assert row["displacement_duration_minutes"] == 90.0
    assert row["detection_source"] == "combined"

    win = db.execute("SELECT COUNT(*) AS c FROM activity_windows").fetchone()["c"]
    assert win == 1


def test_enricher_ignores_other_users_event(fresh_db, monkeypatch):
    db = fresh_db.get_db()
    eid = _task_and_open_event(db, user_id="other-user")
    monkeypatch.setattr(
        "services.event_enricher.ActivityFetcher.is_available", lambda self: True
    )
    # Requesting as a different user must not find (or enrich) the event.
    assert EventEnricher(UID).enrich_pending_event(eid) is None


def test_refresh_profile_state(fresh_db):
    db = fresh_db.get_db()
    _task_and_open_event(db)
    res = InsightGenerator(UID).refresh_profile_state()
    assert res["total_events"] == 1
    assert res["confidence"] == "low"

    row = db.execute("SELECT * FROM profile_state WHERE user_id = ?", (UID,)).fetchone()
    assert row["total_events_analyzed"] == 1
    avoidance = json.loads(row["avoidance_by_type"])
    assert "creative" in avoidance


def test_confidence_thresholds():
    assert confidence_for(0) == "low"
    assert confidence_for(19) == "low"
    assert confidence_for(20) == "medium"
    assert confidence_for(49) == "medium"
    assert confidence_for(50) == "high"
