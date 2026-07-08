"""Background scheduling via APScheduler.

Jobs run once per active user (multi-tenant):
  - hourly: sync tasks (Todoist + plaintext) and enrich open events from AW
  - 09:00 / 19:00 daily: prepare a contextual check-in prompt (stored for the UI)
  - Sunday 18:00: generate the weekly insight report

All jobs are resilient — a failure for one user never stops the others or
crashes the scheduler.
"""
import asyncio
import logging
import threading

import config

logger = logging.getLogger("scheduler")

# Latest agent-prepared check-in prompt per (user_id, checkin_type), surfaced by the API.
_latest_prompt: dict[tuple[str, str], str] = {}
_lock = threading.Lock()


def get_latest_prompt(user_id: str, checkin_type: str = "morning") -> str | None:
    with _lock:
        return _latest_prompt.get((user_id, checkin_type))


def _set_latest_prompt(user_id: str, checkin_type: str, text: str) -> None:
    with _lock:
        _latest_prompt[(user_id, checkin_type)] = text


def _all_user_ids() -> list[str]:
    from auth.db import list_active_user_ids

    try:
        return asyncio.run(list_active_user_ids())
    except Exception as e:  # pragma: no cover
        logger.warning("could not list users for scheduled job: %s", e)
        return []


def run_sync_job():
    from services.task_poller import TaskPoller
    from services.plaintext_watcher import sync_task_file
    from services.event_enricher import EventEnricher

    for uid in _all_user_ids():
        try:
            sync_task_file(config.TASKS_FILE, uid)
            result = TaskPoller(uid).sync()
            enriched = EventEnricher(uid).enrich_all_open_events()
            logger.info("sync job [%s]: %s, enriched=%s", uid, result, enriched)
        except Exception as e:  # pragma: no cover
            logger.warning("sync job failed for user %s: %s", uid, e)


def run_checkin_job(checkin_type: str):
    from agent.orchestrator import ProcrastinationAgent

    for uid in _all_user_ids():
        try:
            question = ProcrastinationAgent(uid).generate_checkin_question(checkin_type)
            _set_latest_prompt(uid, checkin_type, question)
            print(f"\n[Check-in · {checkin_type} · {uid}] {question}")
        except Exception as e:  # pragma: no cover
            logger.warning("checkin job failed for user %s: %s", uid, e)


def run_weekly_report_job():
    from analysis.insight_generator import InsightGenerator

    for uid in _all_user_ids():
        try:
            report = InsightGenerator(uid).generate_weekly_report()
            print(f"\n[Weekly Insight Report · {uid}]\n{report}\n")
        except Exception as e:  # pragma: no cover
            logger.warning("weekly report job failed for user %s: %s", uid, e)


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
