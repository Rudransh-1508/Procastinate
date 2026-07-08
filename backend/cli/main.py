"""Typer CLI for the Procrastination Profiler.

Examples:
    python -m cli.main status
    python -m cli.main checkin "had three meetings, exhausted, kept opening twitter"
    python -m cli.main query "why do I avoid email tasks"
    python -m cli.main report weekly
    python -m cli.main task add "Write Q3 report" --type administrative --est 90 --stakes high
    python -m cli.main log-event <task_id> --delay 26 --displacement entertainment_escape
    python -m cli.main sync
"""
import json

import typer

from db.db import init_db, get_db, generate_id
from datetime import datetime, timezone

app = typer.Typer(help="Procrastination Profiler CLI", no_args_is_help=True)
task_app = typer.Typer(help="Task commands")
report_app = typer.Typer(help="Report commands")
app.add_typer(task_app, name="task")
app.add_typer(report_app, name="report")


def _init():
    init_db()


@app.command()
def status():
    """Show event count and profile confidence."""
    _init()
    from analysis.insight_generator import confidence_for
    import config
    db = get_db()
    events = db.execute("SELECT COUNT(*) AS c FROM procrastination_events").fetchone()["c"]
    tasks = db.execute("SELECT COUNT(*) AS c FROM tasks").fetchone()["c"]
    conf = confidence_for(events)
    typer.echo(f"Tasks logged:        {tasks}")
    typer.echo(f"Procrastination events: {events}")
    typer.echo(f"Profile confidence:  {conf}")
    typer.echo(f"Events to 'high':    {max(0, config.CONFIDENCE_HIGH - events)}")
    typer.echo(f"LLM (Groq) enabled:  {config.llm_enabled()}")


@app.command()
def checkin(text: str):
    """Submit a free-text check-in; prints the structured extraction."""
    _init()
    from services.checkin_parser import CheckinParser
    parser = CheckinParser()
    structured = parser.parse(text)
    task_ids = parser.match_tasks_to_ids(structured.get("tasks_mentioned", []))
    db = get_db()
    db.execute(
        """INSERT INTO checkin_logs
           (id, submitted_at, checkin_type, energy_level, stress_level, social_context,
            hours_of_sleep, had_heavy_meetings, free_text, extracted_data, tasks_mentioned)
           VALUES (?, ?, 'manual', ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            generate_id(), datetime.now(timezone.utc).isoformat(),
            structured.get("energy_level"), structured.get("stress_level"),
            structured.get("social_context"), structured.get("hours_of_sleep"),
            structured.get("had_heavy_meetings"), text,
            json.dumps(structured), json.dumps(task_ids),
        ),
    )
    db.commit()
    typer.echo(json.dumps(structured, indent=2))


@app.command()
def query(message: str):
    """Ask the agent about your patterns."""
    _init()
    from agent.orchestrator import ProcrastinationAgent
    typer.echo(ProcrastinationAgent().run(message))


@app.command()
def sync():
    """Sync tasks (Todoist + plaintext), detect avoidance, enrich from ActivityWatch."""
    _init()
    from services.task_poller import TaskPoller
    from services.plaintext_watcher import sync_task_file
    from services.event_enricher import EventEnricher
    import config
    typer.echo(json.dumps({
        "file": sync_task_file(config.TASKS_FILE),
        "poller": TaskPoller().sync(),
        "enriched": EventEnricher().enrich_all_open_events(),
    }, indent=2))


@app.command("log-event")
def log_event(
    task_id: str,
    delay: float = typer.Option(None, "--delay", help="Delay in hours"),
    displacement: str = typer.Option(None, "--displacement"),
    trigger: str = typer.Option(None, "--trigger", help="Unlock trigger if resolved"),
    energy: int = typer.Option(None, "--energy"),
    stress: int = typer.Option(None, "--stress"),
    notes: str = typer.Option(None, "--notes"),
    resolved: bool = typer.Option(False, "--resolved", help="Mark delay as ended now"),
):
    """Manually log a procrastination event for a task."""
    _init()
    from services.task_poller import _time_of_day
    db = get_db()
    task = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if not task:
        typer.echo(f"Task {task_id} not found", err=True)
        raise typer.Exit(1)
    now = datetime.now(timezone.utc)
    event_id = generate_id()
    db.execute(
        """INSERT INTO procrastination_events
           (id, task_id, detected_at, detection_source, delay_start_at, delay_end_at,
            delay_hours, displacement_type, unlock_trigger, energy_level, stress_level,
            notes, day_of_week, time_of_day, confidence_score)
           VALUES (?, ?, ?, 'checkin', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1.0)""",
        (
            event_id, task_id, now.isoformat(), task["created_at"] or now.isoformat(),
            now.isoformat() if resolved else None, delay, displacement, trigger,
            energy, stress, notes, now.weekday(), _time_of_day(now),
        ),
    )
    db.commit()
    typer.echo(f"Logged event {event_id} for task '{task['title']}'")


@report_app.command("weekly")
def report_weekly():
    """Generate the weekly insight report."""
    _init()
    from analysis.insight_generator import InsightGenerator
    typer.echo(InsightGenerator().generate_weekly_report())


@task_app.command("add")
def task_add(
    title: str,
    type: str = typer.Option("unknown", "--type"),
    est: int = typer.Option(None, "--est", help="Estimated minutes"),
    stakes: str = typer.Option("medium", "--stakes"),
    people: bool = typer.Option(False, "--people", help="Involves other people"),
):
    """Add a task manually."""
    _init()
    db = get_db()
    task_id = generate_id()
    db.execute(
        """INSERT INTO tasks (id, source, title, task_type, estimated_minutes, stakes,
                              involves_other_people, created_at, status, updated_at)
           VALUES (?, 'manual', ?, ?, ?, ?, ?, ?, 'pending', ?)""",
        (task_id, title, type, est, stakes, people,
         datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat()),
    )
    db.commit()
    typer.echo(f"Added task {task_id}: {title}")


@task_app.command("list")
def task_list():
    """List all tasks."""
    _init()
    db = get_db()
    rows = db.execute("SELECT id, title, task_type, status FROM tasks ORDER BY created_at DESC").fetchall()
    if not rows:
        typer.echo("No tasks yet.")
        return
    for r in rows:
        typer.echo(f"  [{r['status']:<8}] {r['title']}  ({r['task_type']})  {r['id']}")


if __name__ == "__main__":
    app()
