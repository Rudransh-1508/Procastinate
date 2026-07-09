"""OPTIONAL demo seeder — populate ~30 days of synthetic data.

The app ships with an EMPTY database by design. Run this only if you want to
see the dashboards/insights populated immediately:

    uv run python seed_demo.py          # add demo data
    uv run python seed_demo.py --wipe   # clear everything first, then seed

It generates realistic tasks, procrastination events (with displacement,
triggers, time-of-day skew), check-ins, and a computed profile.
"""
import argparse
import random
from datetime import timedelta

from db.db import init_db, get_db, generate_id
from timeutil import now_ist
from analysis.insight_generator import InsightGenerator
from cli.main import _local_user_id

random.seed(42)

TASK_TYPES = ["creative", "administrative", "technical", "social", "physical", "collaborative"]
# higher = avoided more often
AVOIDANCE_BIAS = {
    "creative": 0.7, "administrative": 0.85, "social": 0.8,
    "technical": 0.25, "physical": 0.5, "collaborative": 0.6,
}
DISPLACEMENTS = ["productive_procrastination", "entertainment_escape", "social_escape",
                 "communication", "unknown"]
TRIGGERS = ["deadline_pressure", "broke_into_subtasks", "external_ask", "mood_shift",
            "post_win", "forced_start"]
TITLES = {
    "creative": ["Write the client proposal", "Draft the blog post", "Design the deck"],
    "administrative": ["File the expense report", "Reply to onboarding email", "Update the spreadsheet"],
    "technical": ["Fix the login bug", "Refactor the parser", "Write migration script"],
    "social": ["Call the dentist", "Reach out to the new lead", "Schedule the 1:1"],
    "physical": ["Go for a run", "Tidy the desk", "Pick up the package"],
    "collaborative": ["Review teammate's PR", "Prep for the sync", "Write the RFC"],
}
DISP_BY_TIME = {
    "morning": "communication", "afternoon": "productive_procrastination",
    "evening": "entertainment_escape", "night": "social_escape",
}


def _iso(dt):
    return dt.isoformat()


def _time_of_day(h):
    if 5 <= h < 12:
        return "morning"
    if 12 <= h < 17:
        return "afternoon"
    if 17 <= h < 22:
        return "evening"
    return "night"


def wipe(user_id: str):
    db = get_db()
    for t in ["procrastination_events", "activity_windows", "checkin_logs", "insights", "tasks"]:
        db.execute(f"DELETE FROM {t} WHERE user_id = ?", (user_id,))
    db.execute("DELETE FROM profile_state WHERE user_id = ?", (user_id,))
    db.commit()


def seed(user_id: str):
    db = get_db()
    now = now_ist()
    n_events = 0

    for day in range(30, 0, -1):
        date = now - timedelta(days=day)
        # 1-3 avoidance-prone tasks per day
        for _ in range(random.randint(1, 3)):
            ttype = random.choice(TASK_TYPES)
            created = date.replace(hour=random.randint(8, 11), minute=random.randint(0, 59))
            task_id = generate_id()
            est = random.choice([30, 45, 60, 90, 120])
            avoided = random.random() < AVOIDANCE_BIAS[ttype]
            status = "pending" if avoided else "done"
            completed = None if avoided else _iso(created + timedelta(hours=random.uniform(1, 3)))
            db.execute(
                """INSERT INTO tasks (id, user_id, source, title, task_type, estimated_minutes, stakes,
                                      involves_other_people, created_at, completed_at, status, updated_at)
                   VALUES (?, ?, 'manual', ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (task_id, user_id, random.choice(TITLES[ttype]), ttype, est,
                 random.choice(["low", "medium", "high"]),
                 ttype in ("social", "collaborative"),
                 _iso(created), completed, status, _iso(created)),
            )

            if not avoided:
                continue

            # avoidance event — skew detection time toward afternoon/evening
            hour = random.choices(range(24),
                                  weights=[1, 1, 1, 1, 1, 2, 3, 4, 5, 6, 7, 6,
                                           5, 6, 7, 8, 7, 6, 5, 4, 3, 2, 2, 1])[0]
            detected = created.replace(hour=hour, minute=random.randint(0, 59))
            delay_hours = round((detected - created).total_seconds() / 3600 + random.uniform(2, 40), 1)
            tod = _time_of_day(hour)
            resolved = random.random() < 0.55
            disp = DISP_BY_TIME.get(tod) if random.random() < 0.6 else random.choice(DISPLACEMENTS)
            db.execute(
                """INSERT INTO procrastination_events
                   (id, user_id, task_id, detected_at, detection_source, delay_start_at, delay_end_at,
                    delay_hours, displacement_type, displacement_duration_minutes, time_of_day,
                    day_of_week, energy_level, stress_level, unlock_trigger, confidence_score)
                   VALUES (?, ?, ?, ?, 'combined', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0.8)""",
                (
                    generate_id(), user_id, task_id, _iso(detected), _iso(created),
                    _iso(detected + timedelta(hours=2)) if resolved else None,
                    delay_hours, disp, round(random.uniform(20, 120), 1), tod,
                    detected.weekday(), random.randint(1, 5), random.randint(1, 5),
                    random.choice(TRIGGERS) if resolved else None,
                ),
            )
            n_events += 1

        # a check-in most days
        if random.random() < 0.8:
            db.execute(
                """INSERT INTO checkin_logs (id, user_id, submitted_at, checkin_type, energy_level,
                                             stress_level, had_heavy_meetings, hours_of_sleep, free_text)
                   VALUES (?, ?, ?, 'evening', ?, ?, ?, ?, ?)""",
                (generate_id(), user_id, _iso(date.replace(hour=19)), random.randint(1, 5),
                 random.randint(1, 5), random.random() < 0.4, round(random.uniform(5, 8.5), 1),
                 "synthetic check-in"),
            )

    db.commit()
    summary = InsightGenerator(user_id).refresh_profile_state()
    print(f"Seeded {n_events} procrastination events across 30 days.")
    print(f"Profile: {summary}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--wipe", action="store_true", help="Clear all data before seeding")
    ap.add_argument(
        "--user-id",
        default=None,
        help="User to seed (defaults to the local CLI pseudo-user, NOT a real web-app account)",
    )
    args = ap.parse_args()
    init_db()
    uid = args.user_id or _local_user_id()
    if args.wipe:
        wipe(uid)
        print("Wiped existing data.")
    print(f"Seeding for user_id={uid}")
    if not args.user_id:
        print(
            "(This is the local CLI pseudo-user — it won't show up when you log into the "
            "web app with Google. Pass --user-id <your real user id> to seed your web account; "
            "find it via GET /api/users/me while logged in.)"
        )
    seed(uid)
