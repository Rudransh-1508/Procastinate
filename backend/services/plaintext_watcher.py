"""Plain-text task file fallback for users who don't use Todoist.

Format (markdown-style):
    - [ ] Write the client proposal @type:creative @est:90m @stakes:high
    - [x] Reply to onboarding email @type:administrative

Inline metadata: @type:, @est:(m/h), @stakes:, @people:true
"""
import re
from datetime import datetime, timezone
from pathlib import Path

from db.db import get_db, generate_id_from_title

try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer
    _WATCHDOG = True
except ImportError:  # pragma: no cover
    FileSystemEventHandler = object  # type: ignore
    _WATCHDOG = False

_META_RE = re.compile(r"@(\w+):(\S+)")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_task_file(filepath: str) -> dict[str, dict]:
    """Parse a task file into {task_id: {...}}. Returns {} if file missing."""
    path = Path(filepath)
    if not path.exists():
        return {}
    tasks: dict[str, dict] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if line.startswith("- [ ]") or line.startswith("- [x]"):
            done = line.startswith("- [x]")
            content = line[5:].strip()
            meta = _extract_meta(content)
            title = _strip_meta(content)
            if not title:
                continue
            task_id = generate_id_from_title(title)
            tasks[task_id] = {"title": title, "done": done, **meta}
    return tasks


def _extract_meta(content: str) -> dict:
    meta: dict = {}
    for key, val in _META_RE.findall(content):
        if key == "type":
            meta["task_type"] = val
        elif key == "est":
            meta["estimated_minutes"] = _parse_duration(val)
        elif key == "stakes":
            meta["stakes"] = val
        elif key == "people":
            meta["involves_other_people"] = val.lower() in ("true", "yes", "1")
    return meta


def _strip_meta(content: str) -> str:
    return _META_RE.sub("", content).strip()


def _parse_duration(val: str) -> int | None:
    m = re.match(r"(\d+(?:\.\d+)?)\s*(h|hr|hours?|m|min|minutes?)?", val.lower())
    if not m:
        return None
    num = float(m.group(1))
    unit = m.group(2) or "m"
    return int(num * 60) if unit.startswith("h") else int(num)


def sync_task_file(filepath: str) -> dict:
    """Upsert tasks from the file into the DB. Returns counts."""
    db = get_db()
    parsed = parse_task_file(filepath)
    added = updated = 0
    for task_id, t in parsed.items():
        existing = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        status = "done" if t["done"] else "pending"
        if not existing:
            db.execute(
                """INSERT INTO tasks (id, source, title, task_type, estimated_minutes,
                                      stakes, involves_other_people, created_at, status, updated_at)
                   VALUES (?, 'plain_text', ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    task_id, t["title"], t.get("task_type"), t.get("estimated_minutes"),
                    t.get("stakes"), t.get("involves_other_people"),
                    _now_iso(), status, _now_iso(),
                ),
            )
            added += 1
        elif existing["status"] != status:
            done_at = _now_iso() if status == "done" else None
            db.execute(
                "UPDATE tasks SET status=?, completed_at=?, updated_at=? WHERE id=?",
                (status, done_at, _now_iso(), task_id),
            )
            updated += 1
    db.commit()
    return {"added": added, "updated": updated, "total_in_file": len(parsed)}


class TaskFileWatcher(FileSystemEventHandler):
    """Watchdog handler that re-syncs the task file on modification."""

    def __init__(self, filepath: str):
        self.filepath = str(Path(filepath).resolve())

    def on_modified(self, event):  # pragma: no cover - requires fs events
        if getattr(event, "src_path", None) == self.filepath:
            sync_task_file(self.filepath)


def start_watcher(filepath: str):  # pragma: no cover - requires running loop
    """Start a background observer for the task file. Returns observer or None."""
    if not _WATCHDOG:
        return None
    path = Path(filepath)
    if not path.exists():
        return None
    observer = Observer()
    observer.schedule(TaskFileWatcher(filepath), str(path.parent), recursive=False)
    observer.start()
    return observer
