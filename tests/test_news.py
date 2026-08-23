from unittest.mock import Mock, patch

from pipeline.logging_utils import ExchangeLogger
from pipeline.news import _clean_summary, fetch_headlines

SAMPLE_RSS = b"""<?xml version="1.0"?>
<rss version="2.0"><channel>
<title>Test Feed</title>
<item><title>Headline one</title><description>Summary one</description><link>https://example.com/1</link></item>
<item><title>Headline two</title><description>Summary two</description><link>https://example.com/2</link></item>
</channel></rss>"""


def _config():
    return {
        "news": {
            "primary_feed_url": "https://primary.example/rss",
            "fallback_feed_url": "https://fallback.example/rss",
            "max_items": 10,
            "request_timeout_seconds": 5,
        }
    }


def test_clean_summary_strips_html_tags():
    assert _clean_summary("<p>Hello <b>world</b></p>") == "Hello world"


def test_fetch_headlines_uses_primary_feed_when_available():
    logger = ExchangeLogger()
    mock_response = Mock(content=SAMPLE_RSS)
    mock_response.raise_for_status = Mock()
    with patch("pipeline.news.requests.get", return_value=mock_response) as mock_get:
        headlines = fetch_headlines(_config(), logger)
    assert len(headlines) == 2
    assert headlines[0]["title"] == "Headline one"
    mock_get.assert_called_once()


def test_fetch_headlines_falls_back_when_primary_fails():
    logger = ExchangeLogger()
    mock_ok = Mock(content=SAMPLE_RSS)
    mock_ok.raise_for_status = Mock()

    def side_effect(url, *args, **kwargs):
        if "primary" in url:
            raise ConnectionError("boom")
        return mock_ok

    with patch("pipeline.news.requests.get", side_effect=side_effect):
        headlines = fetch_headlines(_config(), logger)
    assert len(headlines) == 2
    assert any(r["status"] == "error" for r in logger.records["news"])


def test_fetch_headlines_returns_empty_list_when_both_sources_fail():
    logger = ExchangeLogger()
    with patch("pipeline.news.requests.get", side_effect=ConnectionError("boom")):
        headlines = fetch_headlines(_config(), logger)
    assert headlines == []
    assert logger.records["news"][-1]["status"] == "all_sources_failed"


def test_fetch_headlines_never_returns_an_excluded_link():
    logger = ExchangeLogger()
    mock_response = Mock(content=SAMPLE_RSS)
    mock_response.raise_for_status = Mock()
    with patch("pipeline.news.requests.get", return_value=mock_response):
        headlines = fetch_headlines(_config(), logger, exclude_links={"https://example.com/1"})
    assert len(headlines) == 1
    assert headlines[0]["link"] == "https://example.com/2"
    assert logger.records["news"][0]["skipped_duplicates"] == 1
