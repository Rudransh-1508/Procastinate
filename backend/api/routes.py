"""All HTTP endpoints for the Procrastination Profiler."""
import json
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
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

router = APIRouter()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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
def get_status():
    db = get_db()
    event_count = db.execute(
        "SELECT COUNT(*) AS c FROM procrastination_events"
    ).fetchone()["c"]
    task_count = db.execute("SELECT COUNT(*) AS c FROM tasks").fetchone()["c"]
    return {
        "total_events": event_count,
        "total_tasks": task_count,
        "profile_confidence": confidence_for(event_count),
        "events_until_high_confidence": max(0, config.CONFIDENCE_HIGH - event_count),
        "llm_enabled": config.llm_enabled(),
    }


@router.get("/dashboard")
def get_dashboard():
    """Single aggregate powering every chart on the dashboard."""
    analyzer = PatternAnalyzer()
    status = get_status()
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
def checkin_prompt(checkin_type: str = "morning"):
    stored = get_latest_prompt(checkin_type)
    if stored:
        return {"prompt": stored, "source": "scheduled"}
    return {
        "prompt": ProcrastinationAgent().generate_checkin_question(checkin_type),
        "source": "live",
    }


@router.post("/checkin")
def submit_checkin(body: CheckinInput):
    parser = CheckinParser()
    structured = parser.parse(body.text)
    task_ids = parser.match_tasks_to_ids(structured.get("tasks_mentioned", []))

    db = get_db()
    db.execute(
        """INSERT INTO checkin_logs
           (id, submitted_at, checkin_type, energy_level, stress_level, social_context,
            hours_of_sleep, had_heavy_meetings, free_text, extracted_data, tasks_mentioned)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            generate_id(), _now_iso(), body.checkin_type,
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
def query_agent(body: QueryInput):
    agent = ProcrastinationAgent()
    response = agent.run(body.message, body.conversation_history)
    return {"response": response}


@router.get("/report/weekly")
def get_weekly_report():
    report = InsightGenerator().generate_weekly_report()
    return {"report": report}


@router.get("/insights")
def list_insights(limit: int = 20):
    db = get_db()
    rows = db.execute(
        "SELECT * FROM insights ORDER BY generated_at DESC LIMIT ?", (limit,)
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
def get_profile():
    db = get_db()
    profile = db.execute("SELECT * FROM profile_state WHERE id = 1").fetchone()
    if not profile:
        return {"status": "no profile yet", "events_needed": config.CONFIDENCE_MEDIUM}
    return _decode_profile(profile)


@router.post("/profile/refresh")
def refresh_profile():
    return InsightGenerator().refresh_profile_state()


# --- tasks / events --------------------------------------------------------
@router.get("/tasks")
def list_tasks(status: str | None = None):
    db = get_db()
    if status:
        rows = db.execute(
            "SELECT * FROM tasks WHERE status = ? ORDER BY created_at DESC", (status,)
        ).fetchall()
    else:
        rows = db.execute("SELECT * FROM tasks ORDER BY created_at DESC").fetchall()
    return {"tasks": [dict(r) for r in rows]}


@router.post("/tasks")
def add_task(body: TaskInput):
    db = get_db()
    task_id = generate_id()
    db.execute(
        """INSERT INTO tasks (id, source, title, task_type, estimated_minutes, stakes,
                              involves_other_people, assigned_by, created_at, status, updated_at)
           VALUES (?, 'manual', ?, ?, ?, ?, ?, ?, ?, 'pending', ?)""",
        (
            task_id, body.title, body.task_type, body.estimated_minutes, body.stakes,
            body.involves_other_people, body.assigned_by, _now_iso(), _now_iso(),
        ),
    )
    db.commit()

    flag = None
    try:
        flag = InsightGenerator().generate_task_flag(body.model_dump())
    except Exception:
        flag = None
    return {"task_id": task_id, "proactive_insight": flag}


@router.get("/events")
def list_events(limit: int = 100):
    db = get_db()
    rows = db.execute(
        """SELECT pe.*, t.title AS task_title, t.task_type
           FROM procrastination_events pe
           LEFT JOIN tasks t ON t.id = pe.task_id
           ORDER BY pe.detected_at DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    return {"events": [dict(r) for r in rows]}


@router.post("/events")
def log_event(body: EventInput):
    """Manually log (or resolve) a procrastination event for a task."""
    db = get_db()
    task = db.execute("SELECT * FROM tasks WHERE id = ?", (body.task_id,)).fetchone()
    if not task:
        raise HTTPException(status_code=404, detail="task not found")

    now = datetime.now(timezone.utc)
    event_id = generate_id()
    db.execute(
        """INSERT INTO procrastination_events
           (id, task_id, detected_at, detection_source, delay_start_at, delay_end_at,
            delay_hours, displacement_type, unlock_trigger, energy_level, stress_level,
            notes, day_of_week, time_of_day, confidence_score)
           VALUES (?, ?, ?, 'checkin', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1.0)""",
        (
            event_id, body.task_id, now.isoformat(),
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
def manual_sync():
    file_res = sync_task_file(config.TASKS_FILE)
    poll_res = TaskPoller().sync()
    enriched = EventEnricher().enrich_all_open_events()
    return {"file": file_res, "poller": poll_res, "enriched": enriched}
