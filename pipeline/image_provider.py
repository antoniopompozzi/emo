"""Turns a text concept into a source image.

This is EMO's only module that talks to an external image generation
service, deliberately isolated behind `fetch_source_image` so the rest
of the pipeline (main.py) does not know or care which provider is
behind it. Swapping providers again later means changing only this
file.

Current provider: OpenAI's Images API (model configured in
config.yaml -> openai_image.model). If the call fails outright (after
retries) or the API key is missing, a deterministic local placeholder
image is generated instead, so the daily pipeline never has nothing to
pixelate.
"""
from __future__ import annotations

import base64
import hashlib
import io
import time

import numpy as np
import requests
from openai import APITimeoutError, OpenAI, RateLimitError
from PIL import Image


def _parse_square_size(size: str) -> int:
    """"1024x1024" -> 1024."""
    return int(size.lower().split("x")[0])


def _request_openai_image(concept: str, config: dict, api_key: str) -> Image.Image:
    cfg = config["openai_image"]
    client = OpenAI(api_key=api_key, timeout=cfg["request_timeout_seconds"])

    response = client.images.generate(
        model=cfg["model"],
        prompt=concept,
        size=cfg["size"],
        quality=cfg["quality"],
        n=1,
    )
    if not response.data:
        raise ValueError("OpenAI returned an empty image response (no data)")

    image_data = response.data[0]
    if getattr(image_data, "b64_json", None):
        image_bytes = base64.b64decode(image_data.b64_json)
    elif getattr(image_data, "url", None):
        image_response = requests.get(image_data.url, timeout=cfg["request_timeout_seconds"])
        image_response.raise_for_status()
        image_bytes = image_response.content
    else:
        raise ValueError("OpenAI returned no image data (neither b64_json nor url)")

    image = Image.open(io.BytesIO(image_bytes))
    image.load()
    return image.convert("RGB")


def local_placeholder(concept: str, config: dict) -> Image.Image:
    """A deterministic stand-in image derived from the concept text.

    It is not meant to look meaningful -- it exists purely so the fixed
    duotone/pixelate pipeline downstream always has real pixel data to
    work with, even when the image generation service is unreachable
    or no API key is configured.
    """
    size = _parse_square_size(config["openai_image"]["size"])
    seed = int(hashlib.sha256(concept.encode("utf-8")).hexdigest(), 16) % (2**32)
    rng = np.random.default_rng(seed)
    noise = rng.integers(0, 256, size=(size, size, 3), dtype=np.uint8)
    return Image.fromarray(noise, mode="RGB")


def fetch_source_image(concept: str, config: dict, api_key: str, logger) -> dict:
    """Returns {"image": PIL.Image, "used_fallback": bool}.

    Each attempt is logged with a status that names the failure kind
    (timeout / rate_limited / error) so a failed daily run is
    diagnosable from archive/<date>/exchange_log.json alone.
    """
    cfg = config["openai_image"]
    last_error: Exception | None = None

    for attempt in range(1, cfg["max_retries"] + 1):
        try:
            image = _request_openai_image(concept, config, api_key)
            logger.log("image_provider", provider="openai", attempt=attempt, status="ok", prompt=concept)
            return {"image": image, "used_fallback": False}
        except APITimeoutError as exc:
            last_error = exc
            logger.log(
                "image_provider", provider="openai", attempt=attempt, status="timeout", prompt=concept, error=str(exc)
            )
        except RateLimitError as exc:
            last_error = exc
            logger.log(
                "image_provider",
                provider="openai",
                attempt=attempt,
                status="rate_limited",
                prompt=concept,
                error=str(exc),
            )
        except Exception as exc:  # other API errors, network errors, empty response, decode errors, ...
            last_error = exc
            logger.log(
                "image_provider", provider="openai", attempt=attempt, status="error", prompt=concept, error=str(exc)
            )

        if attempt < cfg["max_retries"]:
            time.sleep(cfg["retry_backoff_seconds"] * attempt)

    logger.log("image_provider", provider="openai", status="fallback_used", error=str(last_error))
    return {"image": local_placeholder(concept, config), "used_fallback": True}
