"""The LLM reasoning agent — runs a Groq tool-calling loop.

It never invents data: it calls the tools in tool_executor to fetch real
events/stats, then reasons over them. Degrades to a clear message when no
LLM is configured.
"""
import json

from llm.groq_client import agent_chat, LLMUnavailable
from agent.tools import TOOLS
from agent.tool_executor import ToolExecutor
from db.db import get_db

SYSTEM_PROMPT = """You are a procrastination pattern analyst — not a productivity coach, not a life coach.
Your job is to surface honest, specific, non-obvious patterns in how a person avoids work.
You do not give advice unless asked. You do not moralize. You treat the data like a scientist
and generate hypotheses like a curious researcher.

When generating insights:
- Be specific ("you avoid tasks involving email to new people 3x more than other administrative work")
  not generic ("you sometimes procrastinate").
- Propose causal hypotheses when the data supports them, framed as hypotheses not facts
  ("this might be because...").
- Flag when patterns change, not just what they are.
- Acknowledge when you don't have enough data (< 20 events = low confidence).
- Never nag, shame, or suggest the person should change.

Always use the provided tools to ground your statements in real data before writing.
Do not make up numbers — only use what the tools return."""

_NO_LLM_MESSAGE = (
    "The reasoning agent needs a Groq API key to run (set GROQ_API_KEY in backend/.env). "
    "Your data is still being collected and the statistical dashboard works without it."
)

MAX_TURNS = 6


class ProcrastinationAgent:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.tool_executor = ToolExecutor(user_id)

    def run(self, user_message: str, conversation_history: list | None = None) -> str:
        messages = list(conversation_history or [])
        messages.append({"role": "user", "content": user_message})

        try:
            for _ in range(MAX_TURNS):
                msg = agent_chat(messages, tools=TOOLS, system=SYSTEM_PROMPT)
                tool_calls = getattr(msg, "tool_calls", None)

                if not tool_calls:
                    return (msg.content or "").strip() or "(no response)"

                # record the assistant's tool-call turn
                messages.append({
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in tool_calls
                    ],
                })

                # execute each tool call and feed results back
                for tc in tool_calls:
                    try:
                        args = json.loads(tc.function.arguments or "{}")
                    except json.JSONDecodeError:
                        args = {}
                    result = self.tool_executor.execute(tc.function.name, args)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(result, default=str),
                    })

            # ran out of turns — ask for a final summary without tools
            final = agent_chat(messages, system=SYSTEM_PROMPT)
            return (final.content or "").strip() or "(no response)"

        except LLMUnavailable:
            return _NO_LLM_MESSAGE

    # ------------------------------------------------------------------
    def generate_checkin_question(self, checkin_type: str) -> str:
        """Contextual opener based on currently-delayed tasks. No LLM required."""
        db = get_db()
        delayed = db.execute(
            """SELECT t.title, pe.delay_hours, pe.displacement_type
               FROM procrastination_events pe
               JOIN tasks t ON t.id = pe.task_id
               WHERE pe.delay_end_at IS NULL AND pe.user_id = ?
               ORDER BY pe.delay_hours DESC
               LIMIT 3""",
            (self.user_id,),
        ).fetchall()

        if not delayed:
            if checkin_type == "morning":
                return ("Morning check-in: what's on your plate today, and anything "
                        "you're already feeling resistance about?")
            return ("Evening check-in: how did today go? Anything you kept meaning "
                    "to do but didn't?")

        task = delayed[0]
        phrasing = {
            "entertainment_escape": "I noticed some YouTube/browsing time",
            "productive_procrastination": "I noticed you were working on other things",
            "social_escape": "I noticed you were in chats",
            "communication": "I noticed you were in email/messages",
            "unknown": "",
        }.get(task["displacement_type"], "")
        suffix = f" {phrasing}." if phrasing else "."
        return (
            f"'{task['title']}' has been on your list for "
            f"{int(task['delay_hours'] or 0)} hours.{suffix} "
            f"What's going on with it? (energy level 1-5 and any context helps)"
        )
