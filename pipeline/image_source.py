"""Turns a text concept into a source image via Pollinations.ai.

Pollinations requires no API key: a GET request to
https://image.pollinations.ai/prompt/<url-encoded prompt> returns
image bytes directly. If the service is slow or unavailable even after
retries with backoff, a deterministic local placeholder image is
generated instead, so the daily pipeline never has nothing to
pixelate.
"""
from __future__ import annotations

import hashlib
import io
import time
import urllib.parse

import numpy as np
import requests
from PIL import Image


def _request_pollinations(concept: str, config: dict) -> Image.Image:
    poll_cfg = config["pollinations"]
    encoded_prompt = urllib.parse.quote(concept, safe="")
    url = f"{poll_cfg['base_url']}/{encoded_prompt}"
    params = {
        "width": poll_cfg["width"],
        "height": poll_cfg["height"],
        "model": poll_cfg["model"],
        "nologo": "true",
    }
    response = requests.get(url, params=params, timeout=poll_cfg["request_timeout_seconds"])
    response.raise_for_status()
    image = Image.open(io.BytesIO(response.content))
    image.load()
    return image.convert("RGB")


def _local_placeholder(concept: str, config: dict) -> Image.Image:
    """A deterministic stand-in image derived from the concept text.

    It is not meant to look meaningful -- it exists purely so the fixed
    grayscale/pixelate pipeline downstream always has real pixel data
    to work with, even when the free image service is unreachable.
    """
    size = config["pollinations"]["width"]
    seed = int(hashlib.sha256(concept.encode("utf-8")).hexdigest(), 16) % (2**32)
    rng = np.random.default_rng(seed)
    noise = rng.integers(0, 256, size=(size, size, 3), dtype=np.uint8)
    return Image.fromarray(noise, mode="RGB")


def fetch_source_image(concept: str, config: dict, logger) -> dict:
    """Returns {"image": PIL.Image, "used_fallback": bool}."""
    poll_cfg = config["pollinations"]
    last_error = None
    for attempt in range(1, poll_cfg["max_retries"] + 1):
        try:
            image = _request_pollinations(concept, config)
            logger.log("pollinations", attempt=attempt, status="ok", prompt=concept)
            return {"image": image, "used_fallback": False}
        except Exception as exc:
            last_error = exc
            logger.log("pollinations", attempt=attempt, status="error", prompt=concept, error=str(exc))
            if attempt < poll_cfg["max_retries"]:
                time.sleep(poll_cfg["retry_backoff_seconds"] * attempt)

    logger.log("pollinations", status="fallback_used", error=str(last_error))
    return {"image": _local_placeholder(concept, config), "used_fallback": True}
