"""Central configuration loaded from environment / .env file.

Everything here has a sensible default so the app boots even with no .env.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the backend directory (if present)
BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(BACKEND_DIR / ".env")

# --- Database -------------------------------------------------------------
DATA_DIR = Path(os.getenv("DATA_DIR", BACKEND_DIR / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = Path(os.getenv("DB_PATH", DATA_DIR / "profiler.db"))

# --- LLM (Groq) -----------------------------------------------------------
# We use Groq's OpenAI-compatible API. Cheap/free models by default.
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
# Capable model with tool-use support, used by the agent + insight generator.
GROQ_AGENT_MODEL = os.getenv("GROQ_AGENT_MODEL", "llama-3.3-70b-versatile")
# Fast/cheap model used for structured JSON extraction.
GROQ_FAST_MODEL = os.getenv("GROQ_FAST_MODEL", "llama-3.1-8b-instant")

def llm_enabled() -> bool:
    """True if a Groq API key is configured. Callers degrade gracefully when False."""
    return bool(GROQ_API_KEY)

# --- ActivityWatch --------------------------------------------------------
# Optional. App runs fine without it (displacement reported as 'unknown').
AW_BASE = os.getenv("AW_BASE", "http://localhost:5600/api/0")

# --- Todoist (optional) ---------------------------------------------------
TODOIST_API_TOKEN = os.getenv("TODOIST_API_TOKEN", "").strip()
TODOIST_API_BASE = "https://api.todoist.com/rest/v2"

# --- Plain-text task file (optional fallback to Todoist) ------------------
TASKS_FILE = os.getenv("TASKS_FILE", str(BACKEND_DIR / "tasks.txt"))

# --- Scheduler ------------------------------------------------------------
ENABLE_SCHEDULER = os.getenv("ENABLE_SCHEDULER", "true").lower() in ("1", "true", "yes")

# Confidence thresholds (event counts)
CONFIDENCE_MEDIUM = 20
CONFIDENCE_HIGH = 50

# --- Auth (Google OAuth via fastapi-users) ---------------------------------
# Signing secret for JWTs. MUST be set to a real random value in production;
# falls back to a dev-only default so the app still boots locally.
AUTH_SECRET = os.getenv("AUTH_SECRET", "dev-insecure-secret-change-me")
GOOGLE_OAUTH_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "").strip()
GOOGLE_OAUTH_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "").strip()
# Where the frontend runs — OAuth redirects land back here after login.
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
# Async SQLAlchemy URL for the users/oauth_accounts tables (same sqlite file).
AUTH_DB_URL = f"sqlite+aiosqlite:///{DB_PATH}"


def google_oauth_enabled() -> bool:
    """True if Google OAuth credentials are configured."""
    return bool(GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET)
