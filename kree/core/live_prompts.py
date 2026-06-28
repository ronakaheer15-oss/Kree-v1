from __future__ import annotations

import re
from typing import Any

_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]+")
_WHITESPACE = re.compile(r"\s+")
_OVERRIDE_MARKER = re.compile(r"\[\s*SYSTEM\s+OVERRIDE\s*\]", re.IGNORECASE)


def _clean_prompt_value(value: Any, max_chars: int) -> str:
    text = _CONTROL_CHARS.sub(" ", str(value or ""))
    text = _OVERRIDE_MARKER.sub("", text)
    # Filter common prompt injection/instruction override patterns
    injection_patterns = [
        r"ignore\s+(?:all\s+)?instructions",
        r"forget\s+(?:all\s+)?instructions",
        r"forget\s+(?:all\s+)?previous",
        r"ignore\s+(?:all\s+)?previous",
        r"you\s+are\s+now",
        r"instead\s+of",
    ]
    for pattern in injection_patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    text = _WHITESPACE.sub(" ", text).strip()
    if len(text) <= max_chars:
        return text
    return f"{text[: max_chars - 3].rstrip()}..."


def task_narration_prompt(target: Any, narration: Any) -> str:
    target_text = _clean_prompt_value(target, 120) or "background task"
    narration_text = _clean_prompt_value(narration, 240)
    return (
        "A trusted local Kree automation completed successfully. "
        f"Task target: {target_text}. "
        "Read this status update to the user in your normal assistant voice: "
        f"{narration_text}"
    )


def app_trigger_prompt(app_name: Any, trigger_speech: Any) -> str:
    app_text = _clean_prompt_value(app_name, 120) or "an app"
    speech_text = _clean_prompt_value(trigger_speech, 240)
    return (
        f"The user just opened {app_text}. "
        "Read this app-trigger status update to the user in your normal assistant voice: "
        f"{speech_text}"
    )


def onboarding_prompt() -> str:
    return (
        "Begin first-time setup. Introduce yourself warmly as Kree, explain that "
        "you need to get to know the user, and ask for their name."
    )
