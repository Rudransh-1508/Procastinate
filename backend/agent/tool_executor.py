"""Implements the agent's tools against the DB + PatternAnalyzer.

Pure data access — no LLM here. Every handler returns JSON-serializable data.

Security note: `user_id` is bound at construction time from the authenticated
request, NEVER accepted as an LLM-supplied tool argument — the model must not
be able to choose whose data it reads or writes.
"""
import json
from datetime import timedelta

from db.db import get_db
from timeutil import now_ist, iso_ist
from analysis.pattern_analyzer import PatternAnalyzer

VALID_PROFILE_FIELDS = {
    "avoidance_by_type", "avg_delay_hours_by_type", "avoidance_by_hour",
    "avoidance_by_day", "displacement_distribution", "trigger_effectiveness",
    "active_hypotheses", "notable_changes",
}


class ToolExecutor:
    def __init__(self, user_id: str):
        self.user_id = user_id

    def execute(self, tool_name: str, tool_input: dict):
        handlers = {
            "query_procrastination_events": self._query_events,
            "query_profile_state": self._query_profile,
            "run_pattern_analysis": self._run_analysis,
            "update_profile_state": self._update_profile,
            "get_task_details": self._get_task,
        }
        handler = handlers.get(tool_name)
        if not handler:
            return {"error": f"Unknown tool: {tool_name}"}
        try:
            return handler(tool_input or {})
        except Exception as e:
            return {"error": str(e)}

    def _query_events(self, params: dict) -> list:
        db = get_db()
        query = "SELECT * FROM procrastination_events WHERE user_id = ?"
        args: list = [self.user_id]
        if params.get("task_type"):
            # Session-derived events carry task_type directly (no task_id);
            # task-linked events resolve it via the tasks subquery instead.
            query += """ AND (task_type = ? OR task_id IN (
                SELECT id FROM tasks WHERE task_type = ? AND user_id = ?
            ))"""
            args.extend([params["task_type"], params["task_type"], self.user_id])
        if params.get("days_back"):
            cutoff = (now_ist() - timedelta(days=int(params["days_back"]))).isoformat()
            query += " AND detected_at > ?"
            args.append(cutoff)
        if params.get("displacement_type"):
            query += " AND displacement_type = ?"
            args.append(params["displacement_type"])
        if params.get("min_delay_hours") is not None:
            query += " AND delay_hours >= ?"
            args.append(params["min_delay_hours"])
        query += " ORDER BY detected_at DESC LIMIT 200"
        rows = db.execute(query, args).fetchall()
        return [dict(r) for r in rows]

    def _query_profile(self, params: dict) -> dict:
        db = get_db()
        row = db.execute("SELECT * FROM profile_state WHERE user_id = ?", (self.user_id,)).fetchone()
        if not row:
            return {"status": "no profile yet", "events_needed": 20}
        return _decode_profile(row)

    def _run_analysis(self, params: dict) -> dict:
        analyzer = PatternAnalyzer(self.user_id)
        dispatch = {
            "avoidance_by_type": analyzer.avoidance_by_task_type,
            "temporal_heatmap": analyzer.temporal_heatmap,
            "trigger_effectiveness": analyzer.trigger_effectiveness,
            "displacement_distribution": analyzer.displacement_distribution,
            "correlation_matrix": analyzer.correlation_matrix,
            "completion_by_hour": analyzer.completion_rate_by_hour,
            "energy_by_hour": analyzer.energy_by_hour,
        }
        analysis_type = params.get("analysis_type")
        fn = dispatch.get(analysis_type)
        if not fn:
            return {"error": f"Unknown analysis_type: {analysis_type}"}
        return fn()

    def _update_profile(self, params: dict) -> dict:
        field = params.get("field")
        if field not in VALID_PROFILE_FIELDS:
            return {"error": f"Field '{field}' is not an updatable profile field"}
        db = get_db()
        _ensure_profile_row(self.user_id)
        value = params.get("value")
        db.execute(
            f"UPDATE profile_state SET {field} = ?, updated_at = ? WHERE user_id = ?",
            (json.dumps(value), iso_ist(), self.user_id),
        )
        db.commit()
        return {"status": "updated", "field": field, "reason": params.get("reason")}

    def _get_task(self, params: dict) -> dict:
        db = get_db()
        task_id = params.get("task_id")
        task = db.execute(
            "SELECT * FROM tasks WHERE id = ? AND user_id = ?", (task_id, self.user_id)
        ).fetchone()
        if not task:
            return {"error": f"Task {task_id} not found"}
        events = db.execute(
            "SELECT * FROM procrastination_events WHERE task_id = ? AND user_id = ? ORDER BY detected_at",
            (task_id, self.user_id),
        ).fetchall()
        return {"task": dict(task), "events": [dict(e) for e in events]}


# -- helpers ----------------------------------------------------------------
def _ensure_profile_row(user_id: str):
    db = get_db()
    exists = db.execute("SELECT 1 FROM profile_state WHERE user_id = ?", (user_id,)).fetchone()
    if not exists:
        db.execute(
            "INSERT INTO profile_state (user_id, updated_at) VALUES (?, ?)",
            (user_id, iso_ist()),
        )
        db.commit()


_JSON_FIELDS = {
    "avoidance_by_type", "avg_delay_hours_by_type", "avoidance_by_hour",
    "avoidance_by_day", "displacement_distribution", "trigger_effectiveness",
    "active_hypotheses", "notable_changes",
}


def _decode_profile(row) -> dict:
    out = dict(row)
    for f in _JSON_FIELDS:
        if out.get(f):
            try:
                out[f] = json.loads(out[f])
            except (json.JSONDecodeError, TypeError):
                pass
    return out
