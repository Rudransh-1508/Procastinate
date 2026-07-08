"""Statistical pattern analysis — NOT LLM.

The agent calls these as tools; the LLM interprets the results but never
computes them. All methods return JSON-serializable dicts and degrade
gracefully on empty data. Every query is scoped to one user's data.
"""
import numpy as np
from scipy import stats

from db.db import get_db

DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]


class PatternAnalyzer:
    def __init__(self, user_id: str):
        self.user_id = user_id

    def avoidance_by_task_type(self) -> dict:
        db = get_db()
        rows = db.execute(
            """SELECT COALESCE(t.task_type, 'unknown') AS task_type,
                      COUNT(*) AS total_events,
                      AVG(pe.delay_hours) AS avg_delay,
                      COUNT(CASE WHEN pe.delay_end_at IS NOT NULL THEN 1 END) AS completed
               FROM procrastination_events pe
               JOIN tasks t ON t.id = pe.task_id
               WHERE pe.user_id = ?
               GROUP BY task_type""",
            (self.user_id,),
        ).fetchall()

        result = {}
        for row in rows:
            avoidance_rate = 1 - (row["completed"] / max(row["total_events"], 1))
            result[row["task_type"]] = {
                "avoidance_rate": round(avoidance_rate, 2),
                "avg_delay_hours": round(row["avg_delay"] or 0, 1),
                "total_events": row["total_events"],
            }
        return result

    def temporal_heatmap(self) -> dict:
        db = get_db()
        rows = db.execute(
            """SELECT strftime('%H', detected_at) AS hour,
                      strftime('%w', detected_at) AS day_of_week,
                      COUNT(*) AS count
               FROM procrastination_events
               WHERE detected_at IS NOT NULL AND user_id = ?
               GROUP BY hour, day_of_week""",
            (self.user_id,),
        ).fetchall()

        matrix = np.zeros((7, 24))
        for row in rows:
            if row["hour"] is None or row["day_of_week"] is None:
                continue
            matrix[int(row["day_of_week"])][int(row["hour"])] += row["count"]

        total = matrix.sum()
        norm = (matrix / total) if total > 0 else matrix
        return {
            "matrix": norm.tolist(),
            "counts": matrix.tolist(),
            "peak_day": int(matrix.sum(axis=1).argmax()) if total > 0 else None,
            "peak_hour": int(matrix.sum(axis=0).argmax()) if total > 0 else None,
            "days": DAYS,
            "total_events": int(total),
        }

    def trigger_effectiveness(self) -> dict:
        db = get_db()
        rows = db.execute(
            """SELECT unlock_trigger, COUNT(*) AS count,
                      AVG(delay_hours) AS avg_delay_when_used
               FROM procrastination_events
               WHERE unlock_trigger IS NOT NULL AND delay_end_at IS NOT NULL AND user_id = ?
               GROUP BY unlock_trigger""",
            (self.user_id,),
        ).fetchall()
        return {
            row["unlock_trigger"]: {
                "times_used": row["count"],
                "avg_delay_before_trigger": round(row["avg_delay_when_used"] or 0, 1),
            }
            for row in rows
        }

    def displacement_distribution(self) -> dict:
        db = get_db()
        rows = db.execute(
            """SELECT displacement_type, COUNT(*) AS count,
                      AVG(displacement_duration_minutes) AS avg_minutes
               FROM procrastination_events
               WHERE displacement_type IS NOT NULL AND user_id = ?
               GROUP BY displacement_type""",
            (self.user_id,),
        ).fetchall()
        total = sum(r["count"] for r in rows) or 1
        return {
            row["displacement_type"]: {
                "frequency": round(row["count"] / total, 2),
                "avg_duration_minutes": round(row["avg_minutes"] or 0, 1),
            }
            for row in rows
        }

    def correlation_matrix(self) -> dict:
        """Pearson r + p between contextual variables and delay length."""
        db = get_db()
        rows = db.execute(
            """SELECT pe.delay_hours, cl.energy_level, cl.stress_level,
                      cl.had_heavy_meetings, cl.hours_of_sleep
               FROM procrastination_events pe
               LEFT JOIN checkin_logs cl
                 ON date(pe.detected_at) = date(cl.submitted_at) AND cl.user_id = pe.user_id
               WHERE pe.delay_hours IS NOT NULL AND pe.user_id = ?""",
            (self.user_id,),
        ).fetchall()

        if len(rows) < 10:
            return {"error": "Not enough data for correlation analysis (need 10+ events)",
                    "n": len(rows)}

        variables = ["energy_level", "stress_level", "had_heavy_meetings", "hours_of_sleep"]
        result = {}
        for var in variables:
            paired = [(r[var], r["delay_hours"]) for r in rows if r[var] is not None]
            if len(paired) < 5:
                result[var] = {"r": None, "p": None, "note": "insufficient data"}
                continue
            values = [float(p[0]) for p in paired]
            delays = [float(p[1]) for p in paired]
            if len(set(values)) < 2:
                result[var] = {"r": None, "p": None, "note": "no variance"}
                continue
            r, p = stats.pearsonr(values, delays)
            result[var] = {
                "pearson_r": round(float(r), 3),
                "p_value": round(float(p), 4),
                "significant": bool(p < 0.05),
                "direction": "more avoidance" if r > 0 else "less avoidance",
                "n": len(paired),
            }
        return result
