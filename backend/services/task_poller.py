"""Task ingestion: Todoist sync (if configured) + overdue/avoidance detection.

The poller establishes ground truth: *what* was delayed and *for how long*.
It does not know *why* — that's filled in by activity + check-ins later.

Note: TODOIST_API_TOKEN is a single global credential (set in .env), not
per-user — Todoist sync is an optional deployment-wide integration. All
writes are still scoped to the given user_id.
"""
from datetime import datetime, timedelta

import requests

import config
from db.db import get_db, generate_id
from timeutil import now_ist, iso_ist, parse_ist, IST_OFFSET


def _now() -> datetime:
    return now_ist()


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _todoist_created_at_ist(raw: str | None) -> str | None:
    """Todoist returns real UTC timestamps ('...Z'); convert to our IST storage
    convention so delay math against now_ist() stays correct."""
    if not raw:
        return None
    try:
        utc_dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return (utc_dt.replace(tzinfo=None) + IST_OFFSET).isoformat()
    except ValueError:
        return raw


class TaskPoller:
    def __init__(self, user_id: str, api_token: str | None = None):
        self.user_id = user_id
        self.api_token = api_token if api_token is not None else config.TODOIST_API_TOKEN
        self.headers = {"Authorization": f"Bearer {self.api_token}"} if self.api_token else {}

    # -- Todoist ---------------------------------------------------------
    def fetch_tasks(self) -> list[dict]:
        if not self.api_token:
            return []
        resp = requests.get(f"{config.TODOIST_API_BASE}/tasks", headers=self.headers, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def sync(self) -> dict:
        """Pull Todoist tasks (if token), upsert, then run avoidance detection."""
        db = get_db()
        synced = 0
        if self.api_token:
            try:
                tasks = self.fetch_tasks()
            except requests.RequestException:
                tasks = []
            for t in tasks:
                existing = db.execute(
                    "SELECT * FROM tasks WHERE id = ? AND user_id = ?",
                    (str(t["id"]), self.user_id),
                ).fetchone()
                if not existing:
                    db.execute(
                        """INSERT INTO tasks (id, user_id, source, title, description, created_at,
                                              due_at, status, updated_at)
                           VALUES (?, ?, 'todoist', ?, ?, ?, ?, 'pending', ?)""",
                        (
                            str(t["id"]), self.user_id, t.get("content", "untitled"),
                            t.get("description", ""), _todoist_created_at_ist(t.get("created_at")),
                            (t.get("due") or {}).get("date"), _iso(_now()),
                        ),
                    )
                    synced += 1
                elif t.get("is_completed") and existing["status"] != "done":
                    db.execute(
                        "UPDATE tasks SET status='done', completed_at=?, updated_at=? WHERE id=? AND user_id=?",
                        (_iso(_now()), _iso(_now()), str(t["id"]), self.user_id),
                    )
            db.commit()

        detected = self._detect_overdue_tasks()
        return {"synced": synced, "events_detected": detected}

    # -- Avoidance detection (works for ALL sources, incl. manual) -------
    def _detect_overdue_tasks(self) -> int:
        """Flag pending tasks sitting longer than expected as procrastination events."""
        db = get_db()
        now = _now()
        pending = db.execute(
            """SELECT * FROM tasks
               WHERE status = 'pending'
                 AND user_id = ?
                 AND created_at IS NOT NULL
                 AND created_at < ?
                 AND id NOT IN (
                     SELECT task_id FROM procrastination_events
                     WHERE delay_end_at IS NULL AND user_id = ?
                 )""",
            (self.user_id, _iso(now - timedelta(hours=4)), self.user_id),
        ).fetchall()

        count = 0
        for task in pending:
            try:
                created = parse_ist(task["created_at"])
            except (ValueError, AttributeError, TypeError):
                continue
            delay_hours = (now - created).total_seconds() / 3600
            threshold = (task["estimated_minutes"] or 60) / 60
            if delay_hours > max(threshold * 2, 4):
                self._create_pending_event(task, delay_hours)
                count += 1
        return count

    def _create_pending_event(self, task, delay_hours: float):
        db = get_db()
        db.execute(
            """INSERT INTO procrastination_events
               (id, user_id, task_id, detected_at, detection_source, delay_start_at,
                delay_hours, confidence_score, day_of_week, time_of_day)
               VALUES (?, ?, ?, ?, 'task_list', ?, ?, 0.6, ?, ?)""",
            (
                generate_id(), self.user_id, task["id"], _iso(_now()), task["created_at"],
                round(delay_hours, 2),
                _now().weekday(), _time_of_day(_now()),
            ),
        )
        db.commit()


def _time_of_day(dt: datetime) -> str:
    h = dt.hour
    if 5 <= h < 12:
        return "morning"
    if 12 <= h < 17:
        return "afternoon"
    if 17 <= h < 22:
        return "evening"
    return "night"
