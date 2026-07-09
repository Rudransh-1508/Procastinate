"""Insight generation: weekly report, proactive task flags, profile refresh.

The weekly report and task flags use the LLM agent (Groq). The profile
refresh is pure statistics — it recomputes profile_state from the analyzer
so the dashboard and confidence level stay current without an LLM.

Every method is scoped to one user's data.
"""
import json

from db.db import get_db, generate_id
from timeutil import iso_ist
from analysis.pattern_analyzer import PatternAnalyzer
from agent.orchestrator import ProcrastinationAgent
import config

WEEKLY_REPORT_PROMPT = """You have access to a full week of procrastination data for this user.
Generate a weekly insight report that is:
- Honest and specific, not generic
- Focused on 2-3 strong patterns, not an exhaustive list
- Includes at least one causal hypothesis (framed as hypothesis, not fact)
- Notes any changes from the previous week if detectable
- Maximum 300 words
- Tone: curious scientist, not life coach

Use the tools to pull the data you need before writing the report.
Do not make up numbers — only use what the tools return.
Start with the most surprising or non-obvious finding.

Generate this week's insight report now."""


def confidence_for(event_count: int) -> str:
    if event_count < config.CONFIDENCE_MEDIUM:
        return "low"
    if event_count < config.CONFIDENCE_HIGH:
        return "medium"
    return "high"


class InsightGenerator:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.agent = ProcrastinationAgent(user_id)

    def generate_weekly_report(self) -> str:
        report = self.agent.run(WEEKLY_REPORT_PROMPT)
        self._store_insight("weekly_report", "Weekly Insight Report", report)
        return report

    def generate_task_flag(self, task: dict) -> str | None:
        """Flag a newly-added task if its type is historically avoided."""
        profile = _get_profile_dict(self.user_id)
        avoidance_by_type = profile.get("avoidance_by_type") or {}
        if isinstance(avoidance_by_type, str):
            try:
                avoidance_by_type = json.loads(avoidance_by_type)
            except json.JSONDecodeError:
                avoidance_by_type = {}

        task_type = task.get("task_type", "unknown")
        entry = avoidance_by_type.get(task_type, {})
        avoidance_rate = entry.get("avoidance_rate", 0) if isinstance(entry, dict) else 0
        if avoidance_rate < 0.6:
            return None

        flag = self.agent.run(
            f"New task added: '{task.get('title')}' (type: {task_type}). "
            f"Based on the user's history, this task type has a {avoidance_rate:.0%} "
            f"avoidance rate. Generate a single-sentence proactive insight — not a warning, "
            f"just relevant context from their patterns. Use tools to check what typically "
            f"helps for this task type."
        )
        self._store_insight("task_flag", f"Flag: {task.get('title')}", flag,
                            meta={"task_type": task_type, "avoidance_rate": avoidance_rate})
        return flag

    # ------------------------------------------------------------------
    def refresh_profile_state(self) -> dict:
        """Recompute the persistent model from current data (pure stats)."""
        analyzer = PatternAnalyzer(self.user_id)
        db = get_db()

        event_count = db.execute(
            "SELECT COUNT(*) AS c FROM procrastination_events WHERE user_id = ?",
            (self.user_id,),
        ).fetchone()["c"]

        avoidance = analyzer.avoidance_by_task_type()
        heatmap = analyzer.temporal_heatmap()
        displacement = analyzer.displacement_distribution()
        triggers = analyzer.trigger_effectiveness()

        matrix = heatmap.get("counts", [])
        by_hour = [0.0] * 24
        by_day = [0.0] * 7
        if matrix:
            for d in range(7):
                for h in range(24):
                    val = matrix[d][h]
                    by_day[d] += val
                    by_hour[h] += val

        avg_delay = {k: v.get("avg_delay_hours", 0) for k, v in avoidance.items()}

        _ensure_profile_row(self.user_id)
        db.execute(
            """UPDATE profile_state SET
                 updated_at = ?, avoidance_by_type = ?, avg_delay_hours_by_type = ?,
                 avoidance_by_hour = ?, avoidance_by_day = ?, displacement_distribution = ?,
                 trigger_effectiveness = ?, total_events_analyzed = ?, profile_confidence = ?
               WHERE user_id = ?""",
            (
                iso_ist(),
                json.dumps(avoidance), json.dumps(avg_delay),
                json.dumps(by_hour), json.dumps(by_day),
                json.dumps(displacement), json.dumps(triggers),
                event_count, confidence_for(event_count), self.user_id,
            ),
        )
        db.commit()
        return {"total_events": event_count, "confidence": confidence_for(event_count)}

    # ------------------------------------------------------------------
    def _store_insight(self, kind: str, title: str, body: str, meta: dict | None = None):
        db = get_db()
        db.execute(
            """INSERT INTO insights (id, user_id, generated_at, kind, title, body, meta)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (generate_id(), self.user_id, iso_ist(), kind, title,
             body, json.dumps(meta or {})),
        )
        db.commit()


def _ensure_profile_row(user_id: str):
    db = get_db()
    if not db.execute("SELECT 1 FROM profile_state WHERE user_id = ?", (user_id,)).fetchone():
        db.execute(
            "INSERT INTO profile_state (user_id, updated_at) VALUES (?, ?)",
            (user_id, iso_ist()),
        )
        db.commit()


def _get_profile_dict(user_id: str) -> dict:
    db = get_db()
    row = db.execute("SELECT * FROM profile_state WHERE user_id = ?", (user_id,)).fetchone()
    return dict(row) if row else {}
