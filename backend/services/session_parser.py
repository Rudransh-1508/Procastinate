"""Parse free-text session plans and close-outs into structured data.

Primary path: Groq JSON extraction. Fallback: regex/keyword heuristics so
the app still produces usable structure when the LLM is unavailable.

Mirrors services/checkin_parser.py's extract-then-fallback shape.
"""
import re

from llm.groq_client import extract_json, LLMUnavailable

TASK_TYPES = ["creative", "administrative", "technical", "social", "physical", "collaborative"]
DISPLACEMENT_TYPES = [
    "productive_procrastination", "entertainment_escape", "social_escape",
    "communication", "unknown",
]
TRIGGER_TYPES = [
    "deadline_pressure", "broke_into_subtasks", "external_ask",
    "mood_shift", "post_win", "forced_start",
]

PLAN_PROMPT = """You are extracting a time-boxed work plan from a user's own words.

User message: "{text}"

Extract the following fields as JSON:
{{
  "title": short label for the plan (their words, cleaned up), max 60 chars,
  "task_type": one of {task_types} or "unknown",
  "planned_duration_minutes": integer minutes they intend to spend. If they said
    "3 hours" this is 180. If unclear, default to 60.
}}

Return only valid JSON, no explanation."""

CLOSEOUT_PROMPT = """You are extracting what actually happened from a user's own words, closing
out a plan they made to spend {planned_duration_minutes} minutes on: "{planned_text}"

User's close-out message: "{text}"

Extract the following fields as JSON. Use null if not mentioned:
{{
  "completed": true if they did the planned work (even if late), false if they
    did not do it at all and drifted to something else entirely,
  "outcome_hint": one of ["on_time","delayed","not_done"] or null — your best read
    of the situation, purely advisory (the caller computes the real outcome from
    timestamps),
  "actual_delay_minutes": if they give any hint of how late they finished
    relative to plan (e.g. "did it an hour late", "finished around 6pm"),
    your best estimate in minutes, or null,
  "displacement_type": if they drifted, one of {displacement_types} describing
    what they did instead, or null,
  "reason": short summary in their words of why it went the way it did, or null,
  "unlock_trigger": if they mention what finally got them started, one of
    {trigger_types}, or null,
  "energy_level": 1-5 integer or null,
  "stress_level": 1-5 integer or null
}}

Return only valid JSON, no explanation."""


class SessionParser:
    def parse_plan(self, text: str) -> dict:
        """Return {title, task_type, planned_duration_minutes}. Always succeeds."""
        try:
            data = extract_json(
                PLAN_PROMPT.format(text=text, task_types=TASK_TYPES)
            )
            return self._normalize_plan(data, text)
        except LLMUnavailable:
            return self._fallback_plan(text)

    def parse_closeout(self, text: str, planned_text: str, planned_duration_minutes: int) -> dict:
        """Return the closeout fields described in CLOSEOUT_PROMPT. Always succeeds."""
        try:
            data = extract_json(
                CLOSEOUT_PROMPT.format(
                    text=text, planned_text=planned_text,
                    planned_duration_minutes=planned_duration_minutes,
                    displacement_types=DISPLACEMENT_TYPES, trigger_types=TRIGGER_TYPES,
                )
            )
            return self._normalize_closeout(data)
        except LLMUnavailable:
            return self._fallback_closeout(text)

    # ------------------------------------------------------------------
    def _normalize_plan(self, data: dict, text: str) -> dict:
        title = (data.get("title") or "").strip()[:60] or text.strip()[:60]
        task_type = data.get("task_type")
        if task_type not in TASK_TYPES:
            task_type = "unknown"
        duration = _as_positive_int(data.get("planned_duration_minutes"), default=60)
        return {"title": title, "task_type": task_type, "planned_duration_minutes": duration}

    def _fallback_plan(self, text: str) -> dict:
        duration = _parse_duration_minutes(text) or 60
        return {"title": text.strip()[:60], "task_type": "unknown", "planned_duration_minutes": duration}

    # ------------------------------------------------------------------
    def _normalize_closeout(self, data: dict) -> dict:
        outcome_hint = data.get("outcome_hint")
        if outcome_hint not in ("on_time", "delayed", "not_done"):
            outcome_hint = None
        displacement = data.get("displacement_type")
        if displacement not in DISPLACEMENT_TYPES:
            displacement = None
        trigger = data.get("unlock_trigger")
        if trigger not in TRIGGER_TYPES:
            trigger = None
        return {
            "completed": bool(data.get("completed", True)),
            "outcome_hint": outcome_hint,
            "actual_delay_minutes": _as_float(data.get("actual_delay_minutes")),
            "displacement_type": displacement,
            "reason": data.get("reason"),
            "unlock_trigger": trigger,
            "energy_level": _as_int_1_5(data.get("energy_level")),
            "stress_level": _as_int_1_5(data.get("stress_level")),
        }

    def _fallback_closeout(self, text: str) -> dict:
        """Keyword/regex heuristics — used when the LLM is unavailable."""
        t = text.lower()

        not_done_kw = ["didn't", "didnt", "did not", "never got to", "skipped",
                        "avoided", "doomscroll", "scrolling", "ended up", "instead"]
        done_kw = ["done", "finished", "completed", "did it", "wrapped up"]
        completed = not any(k in t for k in not_done_kw) or any(k in t for k in done_kw)

        displacement = None
        for kw, label in [
            ("youtube", "entertainment_escape"), ("reddit", "entertainment_escape"),
            ("scroll", "entertainment_escape"), ("instagram", "entertainment_escape"),
            ("twitter", "entertainment_escape"), ("netflix", "entertainment_escape"),
            ("chat", "social_escape"), ("whatsapp", "social_escape"), ("call", "social_escape"),
            ("email", "communication"), ("message", "communication"),
            ("other project", "productive_procrastination"), ("different task", "productive_procrastination"),
        ]:
            if kw in t:
                displacement = label
                break

        delay_minutes = None
        m = re.search(r"(\d+(?:\.\d+)?)\s*(hour|hr|min)", t)
        if m and any(k in t for k in ["late", "after", "delay"]):
            val = float(m.group(1))
            delay_minutes = val * 60 if m.group(2).startswith("h") else val

        energy = None
        m = re.search(r"(\d+(?:\.\d+)?)\s*/\s*5", t)
        if m:
            energy = _as_int_1_5(m.group(1))

        return {
            "completed": completed,
            "outcome_hint": None,
            "actual_delay_minutes": delay_minutes,
            "displacement_type": displacement if not completed else None,
            "reason": text.strip()[:200] or None,
            "unlock_trigger": None,
            "energy_level": energy,
            "stress_level": None,
        }


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


def _as_positive_int(v, default: int) -> int:
    try:
        n = int(round(float(v)))
        return n if n > 0 else default
    except (TypeError, ValueError):
        return default


def _parse_duration_minutes(text: str) -> int | None:
    t = text.lower()
    total = 0
    found = False
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*(hours?|hrs?|h\b)", t):
        total += float(m.group(1)) * 60
        found = True
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*(minutes?|mins?|m\b)", t):
        total += float(m.group(1))
        found = True
    return int(total) if found else None
