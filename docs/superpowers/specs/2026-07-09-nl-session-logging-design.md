# Natural-Language Session Logging — Design

## 1. Problem

The app currently detects avoidance two ways: (a) a task sitting `pending` past
`max(2× estimate, 4h)`, auto-flagged by `TaskPoller._detect_overdue_tasks`, and
(b) manual logging through `TaskPanel.jsx`'s dropdown form (delay hours,
displacement type, unlock trigger, energy — four separate fields).

Neither matches how the user actually wants to work: state a plan in plain
language ("studying DSA for 3 hours"), then later report what happened in
plain language, with the system inferring drift, reason, and displacement
from that text instead of a form. There is also no "energy/productivity by
time of day" report — only avoidance-by-hour exists, not completion-by-hour,
which is what's needed to answer "should I work when I'm actually sharp."

## 2. Goals / non-goals

**Goals**
- Type a plan → time-boxed session starts, no dropdowns.
- Close out (any time — early, on time, late, or not at all) in plain
  language → system classifies outcome and derives structured fields.
- Sessions that drift feed the *existing* avoidance analytics unchanged.
- All sessions (drifted or not) feed a *new* energy/completion-by-hour report.
- A passive reminder appears when planned time elapses with no close-out.

**Non-goals (this iteration)**
- No passive activity monitoring changes (ActivityWatch integration is
  unaffected; still optional, still enriches `procrastination_events`
  the same way it does today).
- No multi-activity plans ("1h DSA then 1h reading") — one session = one
  intention block.
- Existing Task/Todoist due-date flow and `TaskPanel.jsx` are untouched.
- No push notifications — reminder is a banner shown on page load.

## 3. Data model

New table, `sessions`, scoped by `user_id` like every other domain table:

```sql
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,

    planned_text TEXT NOT NULL,       -- raw NL input, e.g. "studying DSA for 3 hours"
    title TEXT,                       -- short LLM-extracted label
    task_type TEXT,                   -- creative/administrative/technical/social/physical/collaborative

    planned_start TEXT NOT NULL,      -- IST naive timestamp, defaults to now()
    planned_duration_minutes INTEGER NOT NULL,
    planned_end TEXT NOT NULL,        -- computed: planned_start + duration

    status TEXT NOT NULL DEFAULT 'active',  -- active | pending_closeout | closed

    closeout_text TEXT,               -- raw NL input at close-out
    closed_at TEXT,                   -- when close-out was submitted
    outcome TEXT,                     -- early | on_time | delayed | not_done
    delay_minutes REAL,               -- 0 for early/on_time; >0 for delayed
    displacement_type TEXT,           -- same categories as procrastination_events
    reason TEXT,                      -- short LLM summary of what happened
    unlock_trigger TEXT,              -- what got them back to it, if delayed
    energy_level INTEGER,             -- 1-5, if mentioned
    stress_level INTEGER,             -- 1-5, if mentioned

    derived_event_id TEXT,            -- FK-ish: procrastination_events.id if one was derived

    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sessions_user_status ON sessions(user_id, status);
```

**Outcome definitions:**
| Outcome | When | Derives a `procrastination_events` row? |
|---|---|---|
| `early` | closed before `planned_end` | No |
| `on_time` | closed at/after `planned_end`, task was done as planned, no meaningful delay | No |
| `delayed` | done, but later than planned (drift, distraction, then resumed) | Yes |
| `not_done` | not done at all; did something else instead | Yes |

**Derivation into `procrastination_events`:** when a session closes as
`delayed` or `not_done`, insert one row into `procrastination_events` with
`detection_source = 'session'`, `delay_hours` from `delay_minutes / 60`,
`displacement_type`, `time_of_day`/`day_of_week` from `planned_start`,
`energy_level`/`stress_level`, `unlock_trigger`. This is the only new
write path into that table; existing readers (`PatternAnalyzer`,
`agent/tool_executor.py`, the Dashboard, weekly report) require zero changes
to consume it — they already query the table generically, not by
`detection_source`.

## 4. NL parsing (Groq, same pattern as `services/checkin_parser.py`)

Two new prompts in a new `services/session_parser.py`, mirroring the
existing extract-then-fallback structure (`extract_json` primary,
regex/heuristic fallback if the LLM is unavailable):

**`parse_plan(text) -> dict`**
```
{ "title": str, "task_type": one of [...6 categories...] or "unknown",
  "planned_duration_minutes": int }
```
`planned_start` is NOT extracted from text — it is always `now()` (IST) at
submission time, per the user's stated usage ("plans for the next 2-3-4
hours"). Fallback (no LLM): duration parsed via regex for "N hour(s)"/"N
min(s)"; task_type "unknown"; title = first 60 chars of input.

**`parse_closeout(text, planned_duration_minutes) -> dict`**
```
{ "completed": bool, "outcome_hint": "on_time"|"delayed"|"not_done"|null,
  "actual_delay_minutes": float or null,
  "displacement_type": one of [existing 5 categories] or null,
  "reason": str or null, "unlock_trigger": one of [existing trigger enum] or null,
  "energy_level": 1-5 or null, "stress_level": 1-5 or null }
```
The route layer (not the LLM) makes the final `outcome` call — exact timing
is knowable precisely from timestamps, so it is never left to the LLM.
Precise rule, evaluated at close-out submission time (`now`):

1. If `now < planned_end` → `outcome = "early"`, `delay_minutes = 0`.
   (`completed` is assumed true — you only close out something you did.)
2. Else, `delay_minutes = max(0, (actual_completion_time − planned_end))`,
   where `actual_completion_time` is `now` unless the LLM's
   `actual_delay_minutes` gives a more specific estimate (e.g. "finished
   this an hour ago"), in which case `actual_completion_time = now −
   actual_delay_minutes`.
   - If `parse_closeout.completed` is `false` → `outcome = "not_done"`
     regardless of `delay_minutes`.
   - Else if `delay_minutes <= 15` → `outcome = "on_time"` (15-minute grace
     window absorbs "closed out a few minutes late").
   - Else → `outcome = "delayed"`.

Fallback (no LLM): `completed` guessed from keyword scan (similar to today's
`_fallback_parse` in `checkin_parser.py` — negative/avoidance keywords vs.
completion keywords like "done"/"finished"); `actual_delay_minutes` left
null, so `actual_completion_time` defaults to `now`; `displacement_type` =
`unknown`.

## 5. API routes (new, added to `api/routes.py`)

- `POST /api/sessions/start` — body `{ text }`. Runs `parse_plan`, inserts a
  `sessions` row with `status='active'`, returns it.
- `POST /api/sessions/{id}/closeout` — body `{ text }`. Runs `parse_closeout`,
  computes final `outcome`/`delay_minutes` server-side per §4, updates the
  row to `status='closed'`, derives a `procrastination_events` row if
  `outcome` is `delayed`/`not_done`, returns the updated session.
- `GET /api/sessions` — list, most recent first, scoped to caller.
- `GET /api/sessions/active` — the current `active` or `pending_closeout`
  session for the caller, or `null`. Also lazily flips any `active` session
  whose `planned_end` has passed into `pending_closeout` on read (no new
  scheduler job needed for this state transition — checked on-demand,
  consistent with how `EventEnricher`/`TaskPoller` are already invoked both
  by the hourly job and by `POST /sync`/CLI on demand).
- `GET /api/insights/productivity` — new endpoint returning
  `{ energy_by_hour: [24 floats], completion_rate_by_hour: [24 floats],
  peak_hour, trough_hour }`, computed by two new `PatternAnalyzer` methods
  (`energy_by_hour()`, `completion_rate_by_hour()`) that query `sessions`
  directly (not `procrastination_events` — this needs *all* sessions,
  successful ones included, which is why it's a separate table/query).

## 6. Frontend

**New page `Sessions.jsx`**, added to the sidebar nav (between Dashboard and
Check-in). Three states:
1. No active session → single text input, "What's the plan?" + Start button.
2. Active session → live countdown (`planned_end - now`), a persistent
   "Close out" text box + button available at any time (covers finishing
   early).
3. `pending_closeout` (planned time elapsed, unclosed) → the same close-out
   box, but rendered as a banner-styled prompt: *"Your {title} session ended
   {N} ago — what happened?"* This banner also appears at the top of the
   Dashboard if a session is pending, so it's not missed.

Below: a history list of past sessions (title, planned duration, outcome
badge — early/on-time/delayed/not-done — colored consistently with the
existing chip system in `components/ui.jsx`).

**New Dashboard panel**: a small bar/line chart of `completion_rate_by_hour`
and `energy_by_hour` (reuse `Recharts` patterns already used in
`AvoidanceChart.jsx`), with peak/trough hour called out as text, e.g. *"You
complete 80% of sessions started before noon vs. 35% after 9pm."*

The existing `TaskPanel.jsx` (dropdown-based Log avoidance / Mark started /
Complete-task) is untouched — stays available for the secondary Task flow.

## 7. Weekly report integration

`WEEKLY_REPORT_PROMPT` in `analysis/insight_generator.py` gets one addition
to its tool-accessible data: the agent's `run_pattern_analysis` tool gains a
new `analysis_type` option, `"completion_by_hour"`, dispatching to the new
`PatternAnalyzer.completion_rate_by_hour()`. No prompt text changes needed —
the existing instruction ("start with the most surprising finding," "use
tools before writing") already covers using this new tool once it exists.

## 8. Sequencing dependency

Tasks #18 (IST time helper) and #19 (Complete-task action) are already
queued and unimplemented. This feature must land **after** #18: every
timestamp field in `sessions` (`planned_start`, `planned_end`, `closed_at`)
needs to use the same IST-naive convention the rest of the app is being
migrated to, so hour-bucketed queries (`energy_by_hour`,
`completion_rate_by_hour`, the existing temporal heatmap) stay consistent.
Building Sessions on top of un-migrated UTC helpers would mean re-doing the
timestamp logic twice. Recommended order: #18 → #19 → this spec.

## 9. Testing

New `tests/test_session_parser.py` (regex-fallback coverage, same pattern as
`test_checkin_parser.py`) and `tests/test_sessions.py` covering: start →
active; close before `planned_end` → `early`, no derived event; close after
`planned_end` with completion → `delayed`, derived event with correct
`delay_hours`; close after `planned_end` with no completion → `not_done`,
derived event; `GET /api/sessions/active` correctly flips `active` →
`pending_closeout` once `planned_end` has passed.
