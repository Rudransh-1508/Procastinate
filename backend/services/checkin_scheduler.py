"""Background scheduling via APScheduler.

Jobs:
  - hourly: sync tasks (Todoist + plaintext) and enrich open events from AW
  - 09:00 / 19:00 daily: prepare a contextual check-in prompt (stored for the UI)
  - Sunday 18:00: generate the weekly insight report

All jobs are resilient — a failure in one never crashes the scheduler.
"""
import logging
import threading

import config

logger = logging.getLogger("scheduler")

# Latest agent-prepared check-in prompt, surfaced by the API.
_latest_prompt: dict = {"morning": None, "evening": None}
_lock = threading.Lock()


def get_latest_prompt(checkin_type: str = "morning") -> str | None:
    with _lock:
        return _latest_prompt.get(checkin_type)


def _set_latest_prompt(checkin_type: str, text: str) -> None:
    with _lock:
        _latest_prompt[checkin_type] = text


def run_sync_job():
    try:
        from services.task_poller import TaskPoller
        from services.plaintext_watcher import sync_task_file
        from services.event_enricher import EventEnricher

        sync_task_file(config.TASKS_FILE)
        result = TaskPoller().sync()
        enriched = EventEnricher().enrich_all_open_events()
        logger.info("sync job: %s, enriched=%s", result, enriched)
    except Exception as e:  # pragma: no cover
        logger.warning("sync job failed: %s", e)


def run_checkin_job(checkin_type: str):
    try:
        from agent.orchestrator import ProcrastinationAgent
        question = ProcrastinationAgent().generate_checkin_question(checkin_type)
        _set_latest_prompt(checkin_type, question)
        print(f"\n[Check-in · {checkin_type}] {question}")
    except Exception as e:  # pragma: no cover
        logger.warning("checkin job failed: %s", e)


def run_weekly_report_job():
    try:
        from analysis.insight_generator import InsightGenerator
        report = InsightGenerator().generate_weekly_report()
        print(f"\n[Weekly Insight Report]\n{report}\n")
    except Exception as e:  # pragma: no cover
        logger.warning("weekly report job failed: %s", e)


def start_scheduler():
    """Start APScheduler with all jobs. Returns the scheduler (or None if disabled)."""
    if not config.ENABLE_SCHEDULER:
        return None
    from apscheduler.schedulers.background import BackgroundScheduler

    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(run_sync_job, "interval", hours=1, id="hourly_sync")
    scheduler.add_job(lambda: run_checkin_job("morning"), "cron", hour=9, minute=0, id="morning_checkin")
    scheduler.add_job(lambda: run_checkin_job("evening"), "cron", hour=19, minute=0, id="evening_checkin")
    scheduler.add_job(run_weekly_report_job, "cron", day_of_week="sun", hour=18, id="weekly_report")
    scheduler.start()
    logger.info("scheduler started")
    return scheduler
