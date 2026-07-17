"""All HTTP endpoints for the Procrastination Profiler.

Every route requires an authenticated user (Depends(current_active_user))
and every query/write is scoped to that user's own data.
"""
import json
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import config
from db.db import get_db, generate_id
from timeutil import now_ist, iso_ist, parse_ist
from services.checkin_parser import CheckinParser
from services.session_parser import SessionParser
from services.task_poller import TaskPoller, _time_of_day
from services.plaintext_watcher import sync_task_file
from services.event_enricher import EventEnricher
from services.checkin_scheduler import get_latest_prompt
from agent.orchestrator import ProcrastinationAgent
from analysis.pattern_analyzer import PatternAnalyzer
from analysis.insight_generator import InsightGenerator, confidence_for
from agent.tool_executor import _decode_profile
from auth.models import User
from auth.users import current_active_user

router = APIRouter()


def _now_iso() -> str:
    return iso_ist()


def _uid(user: User) -> str:
    return str(user.id)


# --- request models --------------------------------------------------------
class CheckinInput(BaseModel):
    text: str
    checkin_type: str = "manual"


class QueryInput(BaseModel):
    message: str
    conversation_history: list = []


class TaskInput(BaseModel):
    title: str
    task_type: str = "unknown"
    estimated_minutes: int | None = None
    stakes: str = "medium"
    involves_other_people: bool = False
    assigned_by: str = "self"


class EventInput(BaseModel):
    task_id: str
    delay_hours: float | None = None
    displacement_type: str | None = None
    unlock_trigger: str | None = None
    energy_level: int | None = None
    stress_level: int | None = None
    notes: str | None = None
    delay_resolved: bool = False


class SessionStartInput(BaseModel):
    text: str


class SessionCloseoutInput(BaseModel):
    text: str


# --- status / dashboard ----------------------------------------------------
@router.get("/status")
def get_status(user: User = Depends(current_active_user)):
    uid = _uid(user)
    db = get_db()
    event_count = db.execute(
        "SELECT COUNT(*) AS c FROM procrastination_events WHERE user_id = ?", (uid,)
    ).fetchone()["c"]
    task_count = db.execute(
        "SELECT COUNT(*) AS c FROM tasks WHERE user_id = ?", (uid,)
    ).fetchone()["c"]
    return {
        "total_events": event_count,
        "total_tasks": task_count,
        "profile_confidence": confidence_for(event_count),
        "events_until_high_confidence": max(0, config.CONFIDENCE_HIGH - event_count),
        "llm_enabled": config.llm_enabled(),
    }


@router.get("/dashboard")
def get_dashboard(user: User = Depends(current_active_user)):
    """Single aggregate powering every chart on the dashboard."""
    uid = _uid(user)
    analyzer = PatternAnalyzer(uid)
    status = get_status(user)
    return {
        "status": status,
        "avoidance_by_type": analyzer.avoidance_by_task_type(),
        "temporal_heatmap": analyzer.temporal_heatmap(),
        "displacement_distribution": analyzer.displacement_distribution(),
        "trigger_effectiveness": analyzer.trigger_effectiveness(),
        "correlation": analyzer.correlation_matrix(),
    }


@router.get("/insights/productivity")
def get_productivity_insights(user: User = Depends(current_active_user)):
    """Energy/completion by hour-of-day — computed from ALL closed sessions,
    not just avoided ones, so it can answer 'when am I actually productive'."""
    analyzer = PatternAnalyzer(_uid(user))
    energy = analyzer.energy_by_hour()
    completion = analyzer.completion_rate_by_hour()
    return {
        "energy_by_hour": energy["energy_by_hour"],
        "completion_rate_by_hour": completion["completion_rate_by_hour"],
        "counts_by_hour": completion["counts_by_hour"],
        "peak_hour": completion["peak_hour"],
        "trough_hour": completion["trough_hour"],
        "n": completion["n"],
    }


# --- check-in --------------------------------------------------------------
@router.get("/checkin/prompt")
def checkin_prompt(checkin_type: str = "morning", user: User = Depends(current_active_user)):
    uid = _uid(user)
    stored = get_latest_prompt(uid, checkin_type)
    if stored:
        return {"prompt": stored, "source": "scheduled"}
    return {
        "prompt": ProcrastinationAgent(uid).generate_checkin_question(checkin_type),
        "source": "live",
    }


@router.post("/checkin")
def submit_checkin(body: CheckinInput, user: User = Depends(current_active_user)):
    uid = _uid(user)
    parser = CheckinParser()
    structured = parser.parse(body.text)
    task_ids = parser.match_tasks_to_ids(structured.get("tasks_mentioned", []), uid)

    db = get_db()
    db.execute(
        """INSERT INTO checkin_logs
           (id, user_id, submitted_at, checkin_type, energy_level, stress_level, social_context,
            hours_of_sleep, had_heavy_meetings, free_text, extracted_data, tasks_mentioned)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            generate_id(), uid, _now_iso(), body.checkin_type,
            structured.get("energy_level"), structured.get("stress_level"),
            structured.get("social_context"), structured.get("hours_of_sleep"),
            structured.get("had_heavy_meetings"), body.text,
            json.dumps(structured), json.dumps(task_ids),
        ),
    )
    db.commit()
    return {"status": "logged", "extracted": structured, "matched_task_ids": task_ids}


# --- query / reports -------------------------------------------------------
@router.post("/query")
def query_agent(body: QueryInput, user: User = Depends(current_active_user)):
    agent = ProcrastinationAgent(_uid(user))
    response = agent.run(body.message, body.conversation_history)
    return {"response": response}


@router.get("/report/weekly")
def get_weekly_report(user: User = Depends(current_active_user)):
    report = InsightGenerator(_uid(user)).generate_weekly_report()
    return {"report": report}


@router.get("/insights")
def list_insights(limit: int = 20, user: User = Depends(current_active_user)):
    db = get_db()
    rows = db.execute(
        "SELECT * FROM insights WHERE user_id = ? ORDER BY generated_at DESC LIMIT ?",
        (_uid(user), limit),
    ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        if d.get("meta"):
            try:
                d["meta"] = json.loads(d["meta"])
            except json.JSONDecodeError:
                pass
        out.append(d)
    return {"insights": out}


# --- profile ---------------------------------------------------------------
@router.get("/profile")
def get_profile(user: User = Depends(current_active_user)):
    db = get_db()
    profile = db.execute(
        "SELECT * FROM profile_state WHERE user_id = ?", (_uid(user),)
    ).fetchone()
    if not profile:
        return {"status": "no profile yet", "events_needed": config.CONFIDENCE_MEDIUM}
    return _decode_profile(profile)


@router.post("/profile/refresh")
def refresh_profile(user: User = Depends(current_active_user)):
    return InsightGenerator(_uid(user)).refresh_profile_state()


# --- tasks / events --------------------------------------------------------
@router.get("/tasks")
def list_tasks(status: str | None = None, user: User = Depends(current_active_user)):
    uid = _uid(user)
    db = get_db()
    if status:
        rows = db.execute(
            "SELECT * FROM tasks WHERE user_id = ? AND status = ? ORDER BY created_at DESC",
            (uid, status),
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM tasks WHERE user_id = ? ORDER BY created_at DESC", (uid,)
        ).fetchall()
    return {"tasks": [dict(r) for r in rows]}


@router.post("/tasks")
def add_task(body: TaskInput, user: User = Depends(current_active_user)):
    uid = _uid(user)
    db = get_db()
    task_id = generate_id()
    db.execute(
        """INSERT INTO tasks (id, user_id, source, title, task_type, estimated_minutes, stakes,
                              involves_other_people, assigned_by, created_at, status, updated_at)
           VALUES (?, ?, 'manual', ?, ?, ?, ?, ?, ?, ?, 'pending', ?)""",
        (
            task_id, uid, body.title, body.task_type, body.estimated_minutes, body.stakes,
            body.involves_other_people, body.assigned_by, _now_iso(), _now_iso(),
        ),
    )
    db.commit()

    flag = None
    try:
        flag = InsightGenerator(uid).generate_task_flag(body.model_dump())
    except Exception:
        flag = None
    return {"task_id": task_id, "proactive_insight": flag}


@router.post("/tasks/{task_id}/complete")
def complete_task(task_id: str, user: User = Depends(current_active_user)):
    """Mark a task done. Distinct from avoidance logging — this is the only
    action that changes a task's status, so completed tasks stop being
    re-flagged as overdue by the sync job."""
    uid = _uid(user)
    db = get_db()
    task = db.execute(
        "SELECT * FROM tasks WHERE id = ? AND user_id = ?", (task_id, uid)
    ).fetchone()
    if not task:
        raise HTTPException(status_code=404, detail="task not found")

    now = _now_iso()
    db.execute(
        "UPDATE tasks SET status='done', completed_at=?, updated_at=? WHERE id=? AND user_id=?",
        (now, now, task_id, uid),
    )
    # Close any still-open avoidance event for this task so it isn't picked
    # up again by the next sync as "still avoided".
    db.execute(
        """UPDATE procrastination_events SET delay_end_at = ?
           WHERE task_id = ? AND user_id = ? AND delay_end_at IS NULL""",
        (now, task_id, uid),
    )
    db.commit()
    return {"task_id": task_id, "status": "done", "completed_at": now}


@router.get("/events")
def list_events(limit: int = 100, user: User = Depends(current_active_user)):
    db = get_db()
    rows = db.execute(
        """SELECT pe.*, t.title AS task_title,
                  COALESCE(pe.task_type, t.task_type) AS task_type
           FROM procrastination_events pe
           LEFT JOIN tasks t ON t.id = pe.task_id
           WHERE pe.user_id = ?
           ORDER BY pe.detected_at DESC LIMIT ?""",
        (_uid(user), limit),
    ).fetchall()
    return {"events": [dict(r) for r in rows]}


@router.post("/events")
def log_event(body: EventInput, user: User = Depends(current_active_user)):
    """Manually log (or resolve) a procrastination event for a task."""
    uid = _uid(user)
    db = get_db()
    task = db.execute(
        "SELECT * FROM tasks WHERE id = ? AND user_id = ?", (body.task_id, uid)
    ).fetchone()
    if not task:
        raise HTTPException(status_code=404, detail="task not found")

    now = now_ist()
    event_id = generate_id()
    db.execute(
        """INSERT INTO procrastination_events
           (id, user_id, task_id, detected_at, detection_source, delay_start_at, delay_end_at,
            delay_hours, displacement_type, unlock_trigger, energy_level, stress_level,
            notes, day_of_week, time_of_day, confidence_score)
           VALUES (?, ?, ?, ?, 'checkin', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1.0)""",
        (
            event_id, uid, body.task_id, now.isoformat(),
            task["created_at"] or now.isoformat(),
            now.isoformat() if body.delay_resolved else None,
            body.delay_hours, body.displacement_type, body.unlock_trigger,
            body.energy_level, body.stress_level, body.notes,
            now.weekday(), _time_of_day(now),
        ),
    )
    db.commit()
    return {"event_id": event_id}


# --- sync ------------------------------------------------------------------
@router.post("/sync")
def manual_sync(user: User = Depends(current_active_user)):
    uid = _uid(user)
    file_res = sync_task_file(config.TASKS_FILE, uid)
    poll_res = TaskPoller(uid).sync()
    enriched = EventEnricher(uid).enrich_all_open_events()
    return {"file": file_res, "poller": poll_res, "enriched": enriched}


# --- sessions (natural-language plan -> actual logging) ---------------------
GRACE_MINUTES = 15  # delay this small still counts as "on_time"


def _flip_expired_sessions(db, uid: str) -> None:
    """Any 'active' session whose planned_end has passed becomes
    'pending_closeout' — checked lazily on read, no scheduler job needed."""
    db.execute(
        """UPDATE sessions SET status = 'pending_closeout', updated_at = ?
           WHERE user_id = ? AND status = 'active' AND planned_end <= ?""",
        (iso_ist(), uid, iso_ist()),
    )
    db.commit()


@router.post("/sessions/start")
def start_session(body: SessionStartInput, user: User = Depends(current_active_user)):
    uid = _uid(user)
    db = get_db()
    _flip_expired_sessions(db, uid)

    existing = db.execute(
        "SELECT id FROM sessions WHERE user_id = ? AND status IN ('active','pending_closeout')",
        (uid,),
    ).fetchone()
    if existing:
        raise HTTPException(
            status_code=409,
            detail="You already have a session in progress — close it out before starting another.",
        )

    plan = SessionParser().parse_plan(body.text)
    now = now_ist()
    planned_end = now + timedelta(minutes=plan["planned_duration_minutes"])
    session_id = generate_id()
    db.execute(
        """INSERT INTO sessions
           (id, user_id, planned_text, title, task_type, planned_start,
            planned_duration_minutes, planned_end, status, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)""",
        (
            session_id, uid, body.text, plan["title"], plan["task_type"],
            now.isoformat(), plan["planned_duration_minutes"], planned_end.isoformat(),
            iso_ist(), iso_ist(),
        ),
    )
    db.commit()
    return _get_session(db, session_id, uid)


@router.post("/sessions/{session_id}/closeout")
def closeout_session(session_id: str, body: SessionCloseoutInput, user: User = Depends(current_active_user)):
    uid = _uid(user)
    db = get_db()
    _flip_expired_sessions(db, uid)

    session = db.execute(
        "SELECT * FROM sessions WHERE id = ? AND user_id = ?", (session_id, uid)
    ).fetchone()
    if not session:
        raise HTTPException(status_code=404, detail="session not found")
    if session["status"] == "closed":
        raise HTTPException(status_code=409, detail="session already closed")

    parsed = SessionParser().parse_closeout(
        body.text, session["planned_text"], session["planned_duration_minutes"]
    )

    now = now_ist()
    planned_end = parse_ist(session["planned_end"])

    # Outcome is computed here, server-side, from real timestamps — never
    # trusted to the LLM (see design spec §4).
    if now < planned_end:
        outcome = "early"
        delay_minutes = 0.0
    else:
        if not parsed["completed"]:
            outcome = "not_done"
            delay_minutes = max(0.0, (now - planned_end).total_seconds() / 60)
        else:
            actual_completion = now
            if parsed["actual_delay_minutes"] is not None:
                actual_completion = now - timedelta(minutes=parsed["actual_delay_minutes"])
            delay_minutes = max(0.0, (actual_completion - planned_end).total_seconds() / 60)
            outcome = "on_time" if delay_minutes <= GRACE_MINUTES else "delayed"

    displacement_type = parsed["displacement_type"] if outcome in ("delayed", "not_done") else None

    derived_event_id = None
    if outcome in ("delayed", "not_done"):
        planned_start = parse_ist(session["planned_start"])
        derived_event_id = generate_id()
        db.execute(
            """INSERT INTO procrastination_events
               (id, user_id, task_id, task_type, detected_at, detection_source, delay_start_at,
                delay_end_at, delay_hours, displacement_type, energy_level, stress_level, notes,
                unlock_trigger, day_of_week, time_of_day, confidence_score)
               VALUES (?, ?, NULL, ?, ?, 'session', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0.9)""",
            (
                derived_event_id, uid, session["task_type"], iso_ist(), session["planned_start"],
                iso_ist() if outcome == "delayed" else None,
                round(delay_minutes / 60, 3), displacement_type,
                parsed["energy_level"], parsed["stress_level"], parsed["reason"],
                parsed["unlock_trigger"], planned_start.weekday(), _time_of_day(planned_start),
            ),
        )

    db.execute(
        """UPDATE sessions SET
             status = 'closed', closeout_text = ?, closed_at = ?, outcome = ?,
             delay_minutes = ?, displacement_type = ?, reason = ?, unlock_trigger = ?,
             energy_level = ?, stress_level = ?, derived_event_id = ?, updated_at = ?
           WHERE id = ? AND user_id = ?""",
        (
            body.text, iso_ist(), outcome, round(delay_minutes, 1), displacement_type,
            parsed["reason"], parsed["unlock_trigger"], parsed["energy_level"],
            parsed["stress_level"], derived_event_id, iso_ist(), session_id, uid,
        ),
    )
    db.commit()
    return _get_session(db, session_id, uid)


@router.get("/sessions")
def list_sessions(limit: int = 50, user: User = Depends(current_active_user)):
    uid = _uid(user)
    db = get_db()
    _flip_expired_sessions(db, uid)
    rows = db.execute(
        "SELECT * FROM sessions WHERE user_id = ? ORDER BY planned_start DESC LIMIT ?",
        (uid, limit),
    ).fetchall()
    return {"sessions": [dict(r) for r in rows]}


@router.get("/sessions/active")
def get_active_session(user: User = Depends(current_active_user)):
    uid = _uid(user)
    db = get_db()
    _flip_expired_sessions(db, uid)
    row = db.execute(
        """SELECT * FROM sessions WHERE user_id = ? AND status IN ('active', 'pending_closeout')
           ORDER BY planned_start DESC LIMIT 1""",
        (uid,),
    ).fetchone()
    return dict(row) if row else None


def _get_session(db, session_id: str, uid: str) -> dict:
    row = db.execute(
        "SELECT * FROM sessions WHERE id = ? AND user_id = ?", (session_id, uid)
    ).fetchone()
    return dict(row)
