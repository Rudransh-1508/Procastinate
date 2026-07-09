"""IST (Asia/Kolkata, UTC+5:30, no DST) time helpers.

All stored timestamps are naive IST wall-clock strings (no offset suffix)
so SQLite's strftime()-based hour/day bucketing (temporal heatmap, session
hour analysis, correlation-by-date joins) reflects IST directly. Storing an
offset (e.g. "+05:30") would make SQLite's default strftime() output
normalize to UTC internally, which is the opposite of what we want here —
so we deliberately store naive local wall-clock time instead of aware UTC.
"""
from datetime import datetime, timedelta, timezone

IST_OFFSET = timedelta(hours=5, minutes=30)
IST_TZINFO = timezone(IST_OFFSET)  # for aware-datetime contexts (e.g. APScheduler)


def now_ist() -> datetime:
    """Naive datetime representing the current IST wall-clock time."""
    return datetime.now(timezone.utc).replace(tzinfo=None) + IST_OFFSET


def iso_ist(dt: datetime | None = None) -> str:
    """ISO string (no offset) for storage — defaults to now."""
    return (dt or now_ist()).isoformat()


def parse_ist(ts: str) -> datetime:
    """Parse a stored IST timestamp string back into a naive datetime.

    Tolerates legacy rows written before this migration (which may carry a
    'Z' or '+00:00' suffix from the old UTC-based storage) by stripping any
    offset marker — those old values are treated as already being the
    naive wall-clock string for arithmetic purposes.
    """
    cleaned = ts.replace("Z", "").split("+")[0]
    return datetime.fromisoformat(cleaned)


def to_utc_aware(ist_naive: datetime) -> datetime:
    """Convert a naive IST wall-clock datetime to a real aware UTC datetime.

    Only needed at the boundary with external systems that use true UTC
    (e.g. querying the ActivityWatch REST API) — never for our own storage.
    """
    return (ist_naive - IST_OFFSET).replace(tzinfo=timezone.utc)
