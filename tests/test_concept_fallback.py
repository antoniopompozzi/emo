from unittest.mock import Mock, patch

import pytest

from pipeline.concept import FALLBACK_CONCEPT, _extract_json, choose_concept
from pipeline.logging_utils import ExchangeLogger


def test_extract_json_handles_markdown_fences():
    text = '```json\n{"concept": "a cat", "explanation": "because"}\n```'
    parsed = _extract_json(text)
    assert parsed == {"concept": "a cat", "explanation": "because"}


def test_extract_json_rejects_missing_fields():
    with pytest.raises(ValueError):
        _extract_json('{"concept": "a cat"}')


def test_choose_concept_falls_back_after_repeated_failures():
    config = {
        "claude": {
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 100,
            "request_timeout_seconds": 5,
            "max_retries": 2,
            "retry_backoff_seconds": 0,
        }
    }
    logger = ExchangeLogger()
    with patch("pipeline.concept.anthropic.Anthropic") as mock_anthropic_cls:
        mock_client = Mock()
        mock_client.messages.create.side_effect = RuntimeError("api down")
        mock_anthropic_cls.return_value = mock_client
        result = choose_concept([], config, "fake-key", logger)

    assert result["used_fallback"] is True
    assert result["concept"] == FALLBACK_CONCEPT["concept"]
    assert mock_client.messages.create.call_count == 2
