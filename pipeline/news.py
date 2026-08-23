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


def fetch_headlines(config: dict, logger, exclude_links: set[str] | None = None) -> list[dict]:
    """Returns up to `max_items` headlines, trying the primary feed then the fallback.

    `exclude_links` is the set of links already used in previous days (see
    pipeline.archive.previously_used_links): matching entries are dropped,
    so a headline still at the top of the feed isn't picked up again just
    because it hasn't scrolled off yet.
    """
    max_items = config["news"]["max_items"]
    timeout = config["news"]["request_timeout_seconds"]
    exclude_links = exclude_links or set()

    sources = (
        ("bbc_world", config["news"]["primary_feed_url"]),
        ("google_news_world", config["news"]["fallback_feed_url"]),
    )
    for source_name, url in sources:
        try:
            all_items = _fetch_feed(url, timeout)
            fresh_items = [item for item in all_items if item["link"] not in exclude_links]
            skipped = len(all_items) - len(fresh_items)
            items = fresh_items[:max_items]
            logger.log(
                "news", source=source_name, url=url, status="ok",
                item_count=len(items), skipped_duplicates=skipped,
            )
            if items:
                return items
        except Exception as exc:
            logger.log("news", source=source_name, url=url, status="error", error=str(exc))

    logger.log("news", source="none", status="all_sources_failed")
    return []
