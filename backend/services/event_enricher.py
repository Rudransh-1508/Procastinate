"""Cross-reference task-list delays with ActivityWatch displacement data."""
import json

from db.db import get_db, generate_id
from timeutil import parse_ist, to_utc_aware
from services.activity_fetcher import ActivityFetcher, CATEGORY_PRODUCTIVITY


class EventEnricher:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.activity = ActivityFetcher()

    def enrich_pending_event(self, event_id: str) -> dict | None:
        """Enrich one procrastination event with displacement data from AW.

        No-op (returns None) if AW isn't running, the event is missing, or it
        doesn't belong to this user.
        """
        db = get_db()
        event = db.execute(
            "SELECT * FROM procrastination_events WHERE id = ? AND user_id = ?",
            (event_id, self.user_id),
        ).fetchone()
        if not event or not event["delay_start_at"]:
            return None
        if not self.activity.is_available():
            return None

        # Our own storage is naive IST; ActivityWatch's REST API expects real
        # UTC, so convert only at this external-system boundary.
        delay_start = to_utc_aware(parse_ist(event["delay_start_at"]))
        delay_end = to_utc_aware(parse_ist(event["delay_end_at"])) if event["delay_end_at"] else None

        displacement = self.activity.get_displacement_during_delay(delay_start, delay_end)

        # store activity windows
        for w in displacement.get("windows", []):
            db.execute(
                """INSERT OR IGNORE INTO activity_windows
                   (id, user_id, started_at, ended_at, duration_minutes, app_name,
                    window_title, category, productivity_score, related_task_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    generate_id(), self.user_id, w["started_at"], w["ended_at"],
                    w["duration_minutes"], w["app_name"], w["window_title"],
                    w["category"], CATEGORY_PRODUCTIVITY.get(w["category"], 0.4),
                    event["task_id"],
                ),
            )

        db.execute(
            """UPDATE procrastination_events
               SET displacement_type = ?, displacement_apps = ?,
                   displacement_duration_minutes = ?, detection_source = 'combined'
               WHERE id = ? AND user_id = ?""",
            (
                displacement["type"],
                json.dumps([w["app_name"] for w in displacement.get("windows", [])]),
                displacement["total_minutes"],
                event_id, self.user_id,
            ),
        )
        db.commit()
        return displacement

    def enrich_all_open_events(self) -> int:
        """Enrich every still-open (delay_end NULL) event for this user."""
        db = get_db()
        rows = db.execute(
            "SELECT id FROM procrastination_events WHERE displacement_type IS NULL AND user_id = ?",
            (self.user_id,),
        ).fetchall()
        n = 0
        for r in rows:
            if self.enrich_pending_event(r["id"]) is not None:
                n += 1
        return n
