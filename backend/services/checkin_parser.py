"""Parse free-text check-ins into structured data.

Primary path: Groq JSON extraction. Fallback: regex/keyword heuristics so the
app still produces usable structure when the LLM is unavailable.
"""
import re

from llm.groq_client import extract_json, LLMUnavailable
from db.db import get_db

EXTRACTION_PROMPT = """You are extracting structured data from a user's check-in about their procrastination.

User message: "{text}"

Extract the following fields as JSON. Use null if not mentioned:
{{
  "energy_level": 1-5 integer or null,
  "stress_level": 1-5 integer or null,
  "social_context": one of ["just_had_meeting","isolated","normal","social_overload"] or null,
  "hours_of_sleep": float or null,
  "had_heavy_meetings": true/false or null,
  "reason_for_avoidance": short string summary of why they avoided (their words) or null,
  "emotional_texture": one of ["anxiety","boredom","overwhelm","unclear","fatigue","perfectionism","resentment","other"] or null,
  "unlock_hint": what might help them start, if mentioned, or null,
  "tasks_mentioned": list of task title fragments mentioned, or [],
  "sentiment": one of ["negative","neutral","positive"]
}}

Return only valid JSON, no explanation."""


class CheckinParser:
    def parse(self, free_text: str) -> dict:
        """Return structured dict. Always succeeds (falls back to heuristics)."""
        try:
            data = extract_json(EXTRACTION_PROMPT.format(text=free_text))
            return self._normalize(data)
        except LLMUnavailable:
            return self._fallback_parse(free_text)

    # ------------------------------------------------------------------
    def _normalize(self, data: dict) -> dict:
        """Ensure all expected keys exist with safe types."""
        out = {
            "energy_level": _as_int_1_5(data.get("energy_level")),
            "stress_level": _as_int_1_5(data.get("stress_level")),
            "social_context": data.get("social_context"),
            "hours_of_sleep": _as_float(data.get("hours_of_sleep")),
            "had_heavy_meetings": data.get("had_heavy_meetings"),
            "reason_for_avoidance": data.get("reason_for_avoidance"),
            "emotional_texture": data.get("emotional_texture"),
            "unlock_hint": data.get("unlock_hint"),
            "tasks_mentioned": data.get("tasks_mentioned") or [],
            "sentiment": data.get("sentiment") or "neutral",
        }
        if not isinstance(out["tasks_mentioned"], list):
            out["tasks_mentioned"] = []
        return out

    # ------------------------------------------------------------------
    def _fallback_parse(self, text: str) -> dict:
        """Keyword/regex heuristics — used when the LLM is unavailable."""
        t = text.lower()

        # energy / stress as "X/5" or "X/10" or "X out of 5"
        energy = _scan_scale(t, ["energy", "feel"])
        stress = _scan_scale(t, ["stress", "anxious", "overwhelm"])

        # hours of sleep
        sleep = None
        m = re.search(r"(\d+(?:\.\d+)?)\s*(?:hours?|hrs?)\s*(?:of\s*)?sleep", t)
        if m:
            sleep = float(m.group(1))

        heavy_meetings = any(
            k in t for k in ["back-to-back", "back to back", "meetings", "calls", "standup"]
        )
        social_context = "just_had_meeting" if heavy_meetings else (
            "isolated" if any(k in t for k in ["alone", "isolated", "by myself"]) else "normal"
        )

        emotion = None
        for word, label in [
            ("anxious", "anxiety"), ("anxiety", "anxiety"), ("scared", "anxiety"),
            ("bored", "boredom"), ("boring", "boredom"),
            ("overwhelm", "overwhelm"), ("too much", "overwhelm"),
            ("tired", "fatigue"), ("exhausted", "fatigue"), ("drained", "fatigue"),
            ("perfect", "perfectionism"), ("do it justice", "perfectionism"),
            ("resent", "resentment"), ("annoyed", "resentment"),
        ]:
            if word in t:
                emotion = label
                break

        neg = any(k in t for k in ["ugh", "hate", "can't", "cant", "avoid", "stuck", "exhausted", "meh"])
        pos = any(k in t for k in ["finished", "done", "proud", "great", "good day"])
        sentiment = "negative" if neg and not pos else ("positive" if pos and not neg else "neutral")

        return {
            "energy_level": energy,
            "stress_level": stress,
            "social_context": social_context,
            "hours_of_sleep": sleep,
            "had_heavy_meetings": heavy_meetings or None,
            "reason_for_avoidance": text.strip()[:200] if neg else None,
            "emotional_texture": emotion,
            "unlock_hint": None,
            "tasks_mentioned": [],
            "sentiment": sentiment,
        }

    # ------------------------------------------------------------------
    def match_tasks_to_ids(self, mentioned_titles: list[str]) -> list[str]:
        """Fuzzy-match mentioned fragments against pending task titles."""
        if not mentioned_titles:
            return []
        db = get_db()
        tasks = db.execute(
            "SELECT id, title FROM tasks WHERE status='pending'"
        ).fetchall()
        matched: list[str] = []
        for mention in mentioned_titles:
            if not mention:
                continue
            frag = mention.lower()
            for task in tasks:
                if frag in task["title"].lower() or task["title"].lower() in frag:
                    matched.append(task["id"])
                    break
        return matched


# --- small helpers -----------------------------------------------------------
def _as_int_1_5(v):
    try:
        n = int(round(float(v)))
        return min(5, max(1, n))
    except (TypeError, ValueError):
        return None


def _as_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _scan_scale(text: str, near_words: list[str]):
    """Find a 1-5 (or 1-10 normalized to 1-5) rating, optionally near a keyword."""
    # explicit "x/5" or "x/10"
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*/\s*(5|10)", text):
        val, denom = float(m.group(1)), int(m.group(2))
        return _as_int_1_5(val if denom == 5 else val / 2)
    # "x out of 5/10"
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*out of\s*(5|10)", text):
        val, denom = float(m.group(1)), int(m.group(2))
        return _as_int_1_5(val if denom == 5 else val / 2)
    return None
