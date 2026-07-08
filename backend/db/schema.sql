-- Procrastination Profiler — full SQLite schema.
-- Multi-user: every domain table is scoped by user_id (the fastapi-users
-- User.id, a UUID stored as TEXT). Auth tables (users, oauth_account) live
-- in the same .db file but are managed separately via SQLAlchemy — see
-- auth/models.py.

CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,                  -- from Todoist or generated UUID
    user_id TEXT NOT NULL,
    source TEXT,                          -- 'todoist', 'plain_text', 'manual'
    title TEXT NOT NULL,
    description TEXT,
    task_type TEXT,                       -- 'creative','administrative','social',
                                          -- 'technical','physical','collaborative'
    estimated_minutes INTEGER,
    assigned_by TEXT,                     -- 'self' or 'external'
    stakes TEXT,                          -- 'low','medium','high'
    involves_other_people BOOLEAN,
    created_at TIMESTAMP,
    due_at TIMESTAMP,
    completed_at TIMESTAMP,
    status TEXT DEFAULT 'pending',        -- 'pending','in_progress','done','abandoned'
    first_touched_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS procrastination_events (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    task_id TEXT REFERENCES tasks(id),
    detected_at TIMESTAMP,
    detection_source TEXT,               -- 'task_list','activity_watch','checkin','combined'

    -- delay dimensions
    delay_start_at TIMESTAMP,
    delay_end_at TIMESTAMP,
    delay_hours REAL,

    -- avoidance behavior (from ActivityWatch)
    displacement_type TEXT,              -- 'productive_procrastination','entertainment_escape',
                                         -- 'physical_escape','social_escape','unknown'
    displacement_apps TEXT,              -- JSON array of apps
    displacement_duration_minutes REAL,

    -- context at time of avoidance (from check-in)
    time_of_day TEXT,
    day_of_week INTEGER,
    energy_level INTEGER,
    stress_level INTEGER,
    social_context TEXT,
    recent_wins BOOLEAN,
    hours_since_last_break REAL,
    notes TEXT,

    -- trigger that broke avoidance
    unlock_trigger TEXT,

    -- agent-generated fields
    confirmed_by_user BOOLEAN DEFAULT FALSE,
    agent_hypothesis TEXT,
    confidence_score REAL
);

CREATE TABLE IF NOT EXISTS activity_windows (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    duration_minutes REAL,
    app_name TEXT,
    window_title TEXT,
    category TEXT,                       -- 'work','entertainment','social',
                                         -- 'communication','productivity_tool','unknown'
    productivity_score REAL,
    related_task_id TEXT
);

CREATE TABLE IF NOT EXISTS checkin_logs (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    submitted_at TIMESTAMP,
    checkin_type TEXT,                   -- 'morning','evening','triggered','manual'
    energy_level INTEGER,
    stress_level INTEGER,
    social_context TEXT,
    hours_of_sleep REAL,
    had_heavy_meetings BOOLEAN,
    free_text TEXT,
    extracted_data TEXT,                 -- JSON of structured data LLM extracted
    tasks_mentioned TEXT                 -- JSON array of task IDs mentioned
);

CREATE TABLE IF NOT EXISTS profile_state (
    user_id TEXT PRIMARY KEY,            -- one row per user
    updated_at TIMESTAMP,
    avoidance_by_type TEXT,              -- JSON
    avg_delay_hours_by_type TEXT,        -- JSON
    avoidance_by_hour TEXT,              -- JSON 24-element array
    avoidance_by_day TEXT,               -- JSON 7-element array
    displacement_distribution TEXT,      -- JSON
    trigger_effectiveness TEXT,          -- JSON
    active_hypotheses TEXT,              -- JSON array of strings
    total_events_analyzed INTEGER,
    profile_confidence TEXT,             -- 'low','medium','high'
    notable_changes TEXT                 -- JSON
);

CREATE TABLE IF NOT EXISTS insights (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    generated_at TIMESTAMP,
    kind TEXT,                           -- 'weekly_report','task_flag','adhoc'
    title TEXT,
    body TEXT,
    meta TEXT                            -- JSON
);

CREATE INDEX IF NOT EXISTS idx_tasks_user ON tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_events_user ON procrastination_events(user_id);
CREATE INDEX IF NOT EXISTS idx_events_task ON procrastination_events(task_id);
CREATE INDEX IF NOT EXISTS idx_events_detected ON procrastination_events(detected_at);
CREATE INDEX IF NOT EXISTS idx_windows_task ON activity_windows(related_task_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_checkins_user ON checkin_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_insights_user ON insights(user_id);
