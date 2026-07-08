"""Groq LLM wrapper — the ONLY module that talks to an LLM provider.

We use Groq's OpenAI-compatible API. Two entry points:

  - extract_json(prompt)  -> dict   (structured extraction, JSON mode)
  - agent_chat(messages, tools, system) -> message  (tool-calling loop)

Both raise on failure so callers can decide how to degrade gracefully. If no
GROQ_API_KEY is set, LLMUnavailable is raised immediately.
"""
import json
from functools import lru_cache

import config


class LLMUnavailable(RuntimeError):
    """Raised when the LLM cannot be used (no key, network error, bad response)."""


@lru_cache(maxsize=1)
def _client():
    if not config.llm_enabled():
        raise LLMUnavailable("No GROQ_API_KEY configured")
    try:
        from groq import Groq
    except ImportError as e:  # pragma: no cover
        raise LLMUnavailable(f"groq package not installed: {e}")
    return Groq(api_key=config.GROQ_API_KEY)


def extract_json(prompt: str, model: str | None = None) -> dict:
    """Call the fast model in JSON mode and return a parsed dict.

    Raises LLMUnavailable on any failure (no key, network, unparseable output).
    """
    model = model or config.GROQ_FAST_MODEL
    try:
        resp = _client().chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_tokens=600,
            temperature=0.2,
        )
        raw = resp.choices[0].message.content or "{}"
        return json.loads(raw)
    except LLMUnavailable:
        raise
    except json.JSONDecodeError as e:
        raise LLMUnavailable(f"LLM returned invalid JSON: {e}")
    except Exception as e:  # network / API errors
        raise LLMUnavailable(str(e))


def agent_chat(messages: list, tools: list | None = None, system: str | None = None,
               model: str | None = None, max_tokens: int = 1024):
    """Single chat-completion turn for the agent loop.

    `messages` is a list of OpenAI-style message dicts. Returns the raw
    `choices[0].message` object so the caller can inspect `.tool_calls`.
    Raises LLMUnavailable on failure.
    """
    model = model or config.GROQ_AGENT_MODEL
    full_messages = []
    if system:
        full_messages.append({"role": "system", "content": system})
    full_messages.extend(messages)

    kwargs = dict(model=model, messages=full_messages, max_tokens=max_tokens, temperature=0.4)
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"

    try:
        resp = _client().chat.completions.create(**kwargs)
        return resp.choices[0].message
    except LLMUnavailable:
        raise
    except Exception as e:
        raise LLMUnavailable(str(e))
