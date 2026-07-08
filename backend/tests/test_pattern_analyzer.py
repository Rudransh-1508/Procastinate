"""Statistical analyzer tests — synthetic rows in, correct aggregates out."""
from datetime import datetime, timezone

from analysis.pattern_analyzer import PatternAnalyzer
from db.db import generate_id


def _task(db, task_id, task_type):
    db.execute(
        "INSERT INTO tasks (id, source, title, task_type, created_at, status) "
        "VALUES (?, 'manual', ?, ?, ?, 'pending')",
        (task_id, f"task {task_id}", task_type, datetime.now(timezone.utc).isoformat()),
    )


def _event(db, task_id, **kw):
    db.execute(
        """INSERT INTO procrastination_events
           (id, task_id, detected_at, delay_start_at, delay_end_at, delay_hours,
            displacement_type, displacement_duration_minutes, unlock_trigger)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            generate_id(), task_id,
            kw.get("detected_at", "2026-06-01T10:00:00+00:00"),
            "2026-06-01T08:00:00+00:00",
            kw.get("delay_end_at"),
            kw.get("delay_hours", 5.0),
            kw.get("displacement_type"),
            kw.get("displacement_duration_minutes"),
            kw.get("unlock_trigger"),
        ),
    )


def test_avoidance_by_task_type(fresh_db):
    db = fresh_db.get_db()
    _task(db, "t1", "administrative")
    _task(db, "t2", "technical")
    # admin: 2 events, 0 completed -> avoidance 1.0
    _event(db, "t1", delay_hours=10)
    _event(db, "t1", delay_hours=20)
    # technical: 2 events, 1 completed -> avoidance 0.5
    _event(db, "t2", delay_hours=2, delay_end_at="2026-06-01T12:00:00+00:00")
    _event(db, "t2", delay_hours=4)
    db.commit()

    result = PatternAnalyzer().avoidance_by_task_type()
    assert result["administrative"]["avoidance_rate"] == 1.0
    assert result["administrative"]["avg_delay_hours"] == 15.0
    assert result["technical"]["avoidance_rate"] == 0.5
    assert result["technical"]["total_events"] == 2


def test_temporal_heatmap_shape_and_peak(fresh_db):
    db = fresh_db.get_db()
    _task(db, "t1", "creative")
    # three events Monday(=1 in %w? %w: 0=Sunday) at hour 10
    for _ in range(3):
        _event(db, "t1", detected_at="2026-06-01T10:00:00+00:00")  # 2026-06-01 is Monday
    db.commit()

    hm = PatternAnalyzer().temporal_heatmap()
    assert len(hm["matrix"]) == 7
    assert len(hm["matrix"][0]) == 24
    assert hm["total_events"] == 3
    assert hm["peak_hour"] == 10


def test_displacement_distribution(fresh_db):
    db = fresh_db.get_db()
    _task(db, "t1", "creative")
    _event(db, "t1", displacement_type="entertainment_escape", displacement_duration_minutes=60)
    _event(db, "t1", displacement_type="entertainment_escape", displacement_duration_minutes=40)
    _event(db, "t1", displacement_type="productive_procrastination", displacement_duration_minutes=30)
    db.commit()

    dist = PatternAnalyzer().displacement_distribution()
    assert round(dist["entertainment_escape"]["frequency"], 2) == 0.67
    assert dist["productive_procrastination"]["frequency"] == 0.33


def test_trigger_effectiveness(fresh_db):
    db = fresh_db.get_db()
    _task(db, "t1", "creative")
    _event(db, "t1", unlock_trigger="deadline_pressure", delay_hours=8,
           delay_end_at="2026-06-01T18:00:00+00:00")
    _event(db, "t1", unlock_trigger="deadline_pressure", delay_hours=12,
           delay_end_at="2026-06-01T20:00:00+00:00")
    db.commit()

    eff = PatternAnalyzer().trigger_effectiveness()
    assert eff["deadline_pressure"]["times_used"] == 2
    assert eff["deadline_pressure"]["avg_delay_before_trigger"] == 10.0


def test_correlation_insufficient_data(fresh_db):
    db = fresh_db.get_db()
    _task(db, "t1", "creative")
    _event(db, "t1")
    db.commit()
    res = PatternAnalyzer().correlation_matrix()
    assert "error" in res


def test_empty_database_is_safe(fresh_db):
    a = PatternAnalyzer()
    assert a.avoidance_by_task_type() == {}
    assert a.temporal_heatmap()["total_events"] == 0
    assert a.displacement_distribution() == {}
