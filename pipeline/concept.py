"""Asks Claude to freely choose what EMO should depict today.

Claude receives today's headlines and returns a JSON object with:
  - concept: a prompt for the image generation service
  - explanation: a short public-facing rationale (English)
  - emotion: the single dominant emotion evoked by the day's news, one
    of pipeline.emotions.EMOTION_PALETTE's keys -- used downstream to
    pick the duotone color for the pixelation (see postprocess.py).

If the Claude call fails outright, or its response cannot be parsed as
the expected JSON after all retries, a fixed fallback concept is used
so the daily pipeline can still publish something. This is a
deliberate, visible degradation path: `used_fallback` is recorded in
that day's metadata rather than hidden.
"""
from __future__ import annotations

import json
import re
import time

import anthropic

from pipeline.emotions import DEFAULT_EMOTION, EMOTION_PALETTE

_EMOTION_LIST = ", ".join(EMOTION_PALETTE.keys())

SYSTEM_PROMPT = (
    "You are the creative director behind EMO, a daily generative art artifact. "
    "Each day EMO reads international news headlines and freely decides what to "
    "depict: an object, a scene, a reference to a known artwork, an abstract "
    "composition, or anything else the news evokes -- literally, obliquely, or "
    "not at all if you prefer. There are no restrictions on subject or style: "
    "you have total creative freedom.\n\n"
    "Your response becomes three things: (1) a prompt fed directly into an AI "
    "image generation model, (2) a short public explanation of your choice, and "
    "(3) the single dominant emotion the day's news evokes in you.\n\n"
    "Keep in mind that the resulting image will be converted to a black-to-color "
    "duotone (not grayscale), heavily pixelated into a coarse grid of solid "
    "blocks, and reduced to a handful of tones. Favor bold shapes, strong "
    "silhouettes, and clear composition over fine detail or readable text, so "
    "the concept survives that transformation well.\n\n"
    "Respond with ONLY a JSON object, no markdown fences, no commentary, in "
    "exactly this shape:\n"
    '{"concept": "...", "explanation": "...", "emotion": "..."}\n\n'
    "- concept: a detailed visual description (subject, composition, mood, "
    "style/medium) written as an effective prompt for an image generation "
    "model. English only.\n"
    "- explanation: 3-5 sentences, in English, explaining why you chose this "
    "subject/composition in relation to today's news.\n"
    f"- emotion: exactly one word from this fixed list, whichever single "
    f"emotion best captures the overall tone of today's news: {_EMOTION_LIST}. "
    "Use \"neutral\" if nothing dominates."
)

FALLBACK_CONCEPT = {
    "concept": (
        "A single sheet of paper covered edge to edge with tightly packed "
        "horizontal lines of static, like an untuned television screen or an "
        "unreadable telegram, lit from one side so the texture casts long soft "
        "shadows, minimalist studio composition, high contrast, no legible text."
    ),
    "explanation": (
        "Today EMO could not read the news or reason about it -- the usual "
        "signal never arrived. In its place: static, a picture of noise "
        "standing in for information that never reached it. This is not a "
        "comment on the day's events, only an honest record that, on this "
        "occasion, part of the process broke down before the news could be "
        "seen."
    ),
    "emotion": DEFAULT_EMOTION,
}


def _build_user_prompt(headlines: list[dict]) -> str:
    if not headlines:
        return "No headlines were available today. Decide freely what EMO should depict."
    lines = ["Today's international headlines:"]
    for item in headlines:
        line = f"- {item['title']}"
        if item.get("summary"):
            line += f": {item['summary']}"
        lines.append(line)
    return "\n".join(lines)


def _extract_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(json)?|```$", "", text, flags=re.MULTILINE).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object found in Claude's response")
    payload = json.loads(text[start:end + 1])
    if "concept" not in payload or "explanation" not in payload:
        raise ValueError("Claude's JSON is missing required fields")

    # `emotion` only drives a color choice downstream, not the image's
    # subject -- an unrecognized or missing value shouldn't throw away an
    # otherwise good concept/explanation, so this normalizes rather than
    # raising.
    emotion = str(payload.get("emotion", "")).strip().lower()
    if emotion not in EMOTION_PALETTE:
        emotion = DEFAULT_EMOTION

    return {
        "concept": str(payload["concept"]).strip(),
        "explanation": str(payload["explanation"]).strip(),
        "emotion": emotion,
    }


def choose_concept(headlines: list[dict], config: dict, api_key: str, logger) -> dict:
    """Returns {"concept", "explanation", "emotion", "used_fallback"}."""
    claude_cfg = config["claude"]
    client = anthropic.Anthropic(
        api_key=api_key,
        timeout=claude_cfg["request_timeout_seconds"],
        max_retries=0,  # we do our own retries so every attempt can be logged
    )
    user_prompt = _build_user_prompt(headlines)

    last_error = None
    for attempt in range(1, claude_cfg["max_retries"] + 1):
        try:
            response = client.messages.create(
                model=claude_cfg["model"],
                max_tokens=claude_cfg["max_tokens"],
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
            raw_text = "".join(block.text for block in response.content if block.type == "text")
            parsed = _extract_json(raw_text)
            logger.log("claude", attempt=attempt, status="ok", request=user_prompt, response=raw_text)
            parsed["used_fallback"] = False
            return parsed
        except Exception as exc:
            last_error = exc
            logger.log("claude", attempt=attempt, status="error", request=user_prompt, error=str(exc))
            if attempt < claude_cfg["max_retries"]:
                time.sleep(claude_cfg["retry_backoff_seconds"] * attempt)

    logger.log("claude", status="fallback_used", error=str(last_error))
    result = dict(FALLBACK_CONCEPT)
    result["used_fallback"] = True
    return result
