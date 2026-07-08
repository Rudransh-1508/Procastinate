"""ActivityWatch integration — fully optional.

ActivityWatch (https://activitywatch.net) is a local, privacy-first time
tracker exposing a REST API at localhost:5600. If it isn't running, every
method degrades to empty results and the rest of the app keeps working;
displacement is then reported as 'unknown'.
"""
from datetime import datetime, timezone
from typing import Optional

import requests

import config

# App / domain -> displacement category (extensible).
APP_CATEGORIES = {
    # Entertainment escape
    "youtube": "entertainment_escape",
    "netflix": "entertainment_escape",
    "reddit": "entertainment_escape",
    "twitter": "entertainment_escape",
    "x.com": "entertainment_escape",
    "instagram": "entertainment_escape",
    "tiktok": "entertainment_escape",
    # Productive procrastination
    "github": "productive_procrastination",
    "code": "productive_procrastination",        # VS Code
    "cursor": "productive_procrastination",
    "xcode": "productive_procrastination",
    "terminal": "productive_procrastination",
    # Social escape
    "whatsapp": "social_escape",
    "telegram": "social_escape",
    "slack": "social_escape",
    "discord": "social_escape",
    "messages": "social_escape",
    # Communication (ambiguous)
    "gmail": "communication",
    "mail": "communication",
    "outlook": "communication",
    # Work tools
    "notion": "work",
    "figma": "work",
    "linear": "work",
    "docs.google": "work",
}

# Category -> rough productivity score (0..1) for activity_windows.
CATEGORY_PRODUCTIVITY = {
    "work": 0.9,
    "productive_procrastination": 0.5,
    "communication": 0.5,
    "social_escape": 0.2,
    "entertainment_escape": 0.05,
    "physical_escape": 0.3,
    "unknown": 0.4,
}


class ActivityFetcher:
    def __init__(self, base: str | None = None):
        self.base = base or config.AW_BASE

    def is_available(self) -> bool:
        try:
            r = requests.get(f"{self.base}/buckets", timeout=1.5)
            return r.status_code == 200
        except requests.RequestException:
            return False

    def get_buckets(self) -> list[str]:
        try:
            resp = requests.get(f"{self.base}/buckets", timeout=3)
            resp.raise_for_status()
            return list(resp.json().keys())
        except requests.RequestException:
            return []

    def get_events(self, start: datetime, end: datetime,
                   bucket_prefix: str = "aw-watcher-window") -> list[dict]:
        buckets = [b for b in self.get_buckets() if b.startswith(bucket_prefix)]
        all_events: list[dict] = []
        for bucket in buckets:
            try:
                resp = requests.get(
                    f"{self.base}/buckets/{bucket}/events",
                    params={"start": start.isoformat(), "end": end.isoformat(), "limit": 10000},
                    timeout=5,
                )
                resp.raise_for_status()
                all_events.extend(resp.json())
            except requests.RequestException:
                continue
        return sorted(all_events, key=lambda e: e.get("timestamp", ""))

    def categorize_event(self, event: dict) -> str:
        data = event.get("data", {})
        app = str(data.get("app", "")).lower()
        title = str(data.get("title", "")).lower()
        for keyword, category in APP_CATEGORIES.items():
            if keyword in app or keyword in title:
                return category
        return "unknown"

    def build_activity_windows(self, start: datetime, end: datetime) -> list[dict]:
        """Merge raw AW events into contiguous same-category blocks."""
        events = self.get_events(start, end)
        if not events:
            return []
        windows: list[dict] = []
        current = None
        for event in events:
            category = self.categorize_event(event)
            duration = float(event.get("duration", 0) or 0)  # seconds
            data = event.get("data", {})
            if current and current["category"] == category:
                current["duration_minutes"] += duration / 60
                current["ended_at"] = event["timestamp"]
            else:
                if current:
                    windows.append(current)
                current = {
                    "started_at": event["timestamp"],
                    "ended_at": event["timestamp"],
                    "app_name": data.get("app", "unknown"),
                    "window_title": data.get("title", ""),
                    "category": category,
                    "duration_minutes": duration / 60,
                }
        if current:
            windows.append(current)
        return windows

    def get_displacement_during_delay(self, delay_start: datetime,
                                      delay_end: Optional[datetime]) -> dict:
        """Return the 'displacement signature' for a delay window."""
        end = delay_end or datetime.now(timezone.utc)
        windows = self.build_activity_windows(delay_start, end)
        if not windows:
            return {"type": "unknown", "breakdown": {}, "total_minutes": 0, "windows": []}

        time_by_category: dict[str, float] = {}
        for w in windows:
            time_by_category[w["category"]] = (
                time_by_category.get(w["category"], 0) + w["duration_minutes"]
            )
        total = sum(time_by_category.values()) or 1
        breakdown = {k: round(v / total, 2) for k, v in time_by_category.items()}
        dominant = max(time_by_category, key=time_by_category.get)
        return {
            "type": dominant,
            "breakdown": breakdown,
            "total_minutes": round(total, 1),
            "windows": windows,
        }
