"""Asks Claude to synthesize a week of EMO's own interpretations into ORACLE.

Unlike concept.py, this does not read the news -- it rereads the
concept/explanation Claude itself wrote for each of the previous seven
EMO days (see pipeline.archive.load_recent_days) and asks it to
imagine what future awaits humanity based on that week alone. Claude
returns a JSON object with:
  - concept: a prompt for the image generation service
  - explanation: a short public-facing description of the perceived
    mood/trajectory only -- never a specific fact, news item, or
    headline from the week
  - verdict: "positive" or "negative", one of
    pipeline.oracle_palette.ORACLE_PALETTE's keys -- used downstream to
    pick ORACLE's binary duotone color (see postprocess.py).

If the Claude call fails outright, or its response cannot be parsed as
the expected JSON after all retries, a fixed fallback concept is used,
same degradation model as concept.py's FALLBACK_CONCEPT:
`used_fallback` is recorded rather than hidden.
"""
from __future__ import annotations

import json
import re
import time

import anthropic

from pipeline.oracle_palette import DEFAULT_VERDICT, ORACLE_PALETTE

SYSTEM_PROMPT = (
    "You are ORACLE, a weekly generative art artifact that is part of EMO. "
    "Every day EMO reads international news and freely decides what to depict, "
    "recording a concept (image prompt) and an explanation for each day. You are "
    "not reading the news itself -- you are rereading EMO's own seven most recent "
    "daily interpretations, given to you below as this week's concept and "
    "explanation for each day. Based only on that week of EMO's own readings, "
    "imagine what future awaits humanity, and freely decide what ORACLE should "
    "depict.\n\n"
    "Your response becomes three things: (1) a prompt fed directly into an AI "
    "image generation model, (2) a short public explanation of your choice, and "
    "(3) a binary verdict on the future you perceive.\n\n"
    "Keep in mind that the resulting image will be converted to a black-to-color "
    "duotone, heavily pixelated into a coarse grid of solid blocks, and reduced "
    "to a handful of tones -- favor bold shapes, strong silhouettes, and clear "
    "composition over fine detail or readable text, so the concept survives that "
    "transformation well.\n\n"
    "Respond with ONLY a JSON object, no markdown fences, no commentary, in "
    "exactly this shape:\n"
    '{"concept": "...", "explanation": "...", "verdict": "..."}\n\n'
    "- concept: a detailed visual description (subject, composition, mood, "
    "style/medium) written as an effective prompt for an image generation "
    "model. English only.\n"
    "- explanation: 3-5 sentences, in English, describing ONLY the atmosphere or "
    "trajectory you perceive in humanity's future based on this week. Do NOT "
    "state, reference, summarize, or allude to any specific fact, news item, "
    "event, or headline from the week -- explanation must read as a forecast of "
    "mood and direction, never as a recap of what happened.\n"
    '- verdict: exactly one word, either "positive" or "negative" -- whichever '
    "single verdict best captures the future you perceive for humanity based on "
    "this week's seven interpretations."
)

FALLBACK_CONCEPT = {
    "concept": (
        "A vast horizon split evenly between total darkness and a faint pale "
        "glow, seen from a great distance, no figures, no landmarks, just the "
        "line where the two halves meet, minimalist, high contrast, no legible "
        "text."
    ),
    "explanation": (
        "This week ORACLE could not synthesize the past seven days -- the usual "
        "signal never arrived. In its place: an undecided horizon, a picture of "
        "a verdict withheld rather than reasoned. This is not a forecast, only "
        "an honest record that, on this occasion, part of the process broke "
        "down before this week could be read."
    ),
    "verdict": DEFAULT_VERDICT,
}


def _build_user_prompt(days: list[dict]) -> str:
    if not days:
        return "No days from this week were available. Decide freely what ORACLE should depict."
    lines = ["This week's EMO interpretations, oldest to newest:"]
    for item in days:
        lines.append(f"- {item['date']}: {item['concept']} -- {item['explanation']}")
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

    # `verdict` only drives a color choice downstream, not the image's
    # subject -- an unrecognized or missing value shouldn't throw away an
    # otherwise good concept/explanation, so this normalizes rather than
    # raising. Defaults to "negative": an ambiguous reading of the week
    # should not be presented as reassuring.
    verdict = str(payload.get("verdict", "")).strip().lower()
    if verdict not in ORACLE_PALETTE:
        verdict = DEFAULT_VERDICT

    return {
        "concept": str(payload["concept"]).strip(),
        "explanation": str(payload["explanation"]).strip(),
        "verdict": verdict,
    }


def choose_concept(days: list[dict], config: dict, api_key: str, logger) -> dict:
    """Returns {"concept", "explanation", "verdict", "used_fallback"}."""
    claude_cfg = config["claude"]
    client = anthropic.Anthropic(
        api_key=api_key,
        timeout=claude_cfg["request_timeout_seconds"],
        max_retries=0,  # we do our own retries so every attempt can be logged
    )
    user_prompt = _build_user_prompt(days)

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
