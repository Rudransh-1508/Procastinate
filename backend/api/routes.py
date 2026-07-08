"""All HTTP endpoints for the Procrastination Profiler.

Every route requires an authenticated user (Depends(current_active_user))
and every query/write is scoped to that user's own data.
"""
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import config
from db.db import get_db, generate_id
from services.checkin_parser import CheckinParser
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
    return datetime.now(timezone.utc).isoformat()


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


@router.get("/events")
def list_events(limit: int = 100, user: User = Depends(current_active_user)):
    db = get_db()
    rows = db.execute(
        """SELECT pe.*, t.title AS task_title, t.task_type
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

    now = datetime.now(timezone.utc)
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
