"""Fetches today's headlines from a free RSS feed.

Primary source: BBC World News. If that is unreachable or returns no
items, falls back to Google News' World section (English).
"""
from __future__ import annotations

import re

import feedparser
import requests

USER_AGENT = "EMO-pixel-art-bot/1.0 (+https://github.com/)"


def _clean_summary(raw_html: str) -> str:
    # RSS summaries often carry HTML; strip tags with a small, dependency-free pass.
    text = re.sub(r"<[^>]+>", " ", raw_html)
    return re.sub(r"\s+", " ", text).strip()


def _fetch_feed(url: str, timeout: int) -> list[dict]:
    response = requests.get(url, timeout=timeout, headers={"User-Agent": USER_AGENT})
    response.raise_for_status()
    parsed = feedparser.parse(response.content)
    if parsed.bozo and not parsed.entries:
        raise ValueError(f"feed could not be parsed: {parsed.bozo_exception}")

    items = []
    for entry in parsed.entries:
        items.append({
            "title": entry.get("title", "").strip(),
            "summary": _clean_summary(entry.get("summary", "")),
            "link": entry.get("link", ""),
        })
    return items


def fetch_headlines(config: dict, logger) -> list[dict]:
    """Returns up to `max_items` headlines, trying the primary feed then the fallback."""
    max_items = config["news"]["max_items"]
    timeout = config["news"]["request_timeout_seconds"]

    sources = (
        ("bbc_world", config["news"]["primary_feed_url"]),
        ("google_news_world", config["news"]["fallback_feed_url"]),
    )
    for source_name, url in sources:
        try:
            items = _fetch_feed(url, timeout)[:max_items]
            logger.log("news", source=source_name, url=url, status="ok", item_count=len(items))
            if items:
                return items
        except Exception as exc:
            logger.log("news", source=source_name, url=url, status="error", error=str(exc))

    logger.log("news", source="none", status="all_sources_failed")
    return []
