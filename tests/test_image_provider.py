import base64
import io
from unittest.mock import Mock, patch

import numpy as np
from PIL import Image

from pipeline.image_provider import fetch_source_image, local_placeholder
from pipeline.logging_utils import ExchangeLogger


def _config():
    return {
        "openai_image": {
            "model": "gpt-image-1.5",
            "quality": "medium",
            "size": "8x8",  # small on purpose -- these tests never hit the real API
            "request_timeout_seconds": 5,
            "max_retries": 2,
            "retry_backoff_seconds": 0,
        }
    }


def test_local_placeholder_is_deterministic_for_the_same_concept():
    config = _config()
    image_a = local_placeholder("a red bicycle", config)
    image_b = local_placeholder("a red bicycle", config)
    assert np.array_equal(np.array(image_a), np.array(image_b))
    assert image_a.size == (8, 8)


def test_local_placeholder_differs_for_different_concepts():
    config = _config()
    image_a = local_placeholder("a red bicycle", config)
    image_b = local_placeholder("a blue umbrella", config)
    assert not np.array_equal(np.array(image_a), np.array(image_b))


def test_fetch_source_image_falls_back_after_repeated_failures():
    config = _config()
    logger = ExchangeLogger()
    with patch("pipeline.image_provider.OpenAI") as mock_openai_cls:
        mock_client = Mock()
        mock_client.images.generate.side_effect = RuntimeError("api down")
        mock_openai_cls.return_value = mock_client
        result = fetch_source_image("a red bicycle", config, "fake-key", logger)

    assert result["used_fallback"] is True
    assert result["image"].size == (8, 8)
    assert mock_client.images.generate.call_count == 2
    statuses = [r["status"] for r in logger.records["image_provider"]]
    assert statuses == ["error", "error", "fallback_used"]


def test_fetch_source_image_returns_decoded_image_on_success():
    config = _config()
    logger = ExchangeLogger()

    sample = Image.new("RGB", (4, 4), color=(10, 20, 30))
    buf = io.BytesIO()
    sample.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")

    mock_response = Mock(data=[Mock(b64_json=b64, url=None)])

    with patch("pipeline.image_provider.OpenAI") as mock_openai_cls:
        mock_client = Mock()
        mock_client.images.generate.return_value = mock_response
        mock_openai_cls.return_value = mock_client
        result = fetch_source_image("a red bicycle", config, "fake-key", logger)

    assert result["used_fallback"] is False
    assert result["image"].size == (4, 4)
    assert logger.records["image_provider"][-1]["status"] == "ok"


def test_fetch_source_image_raises_clear_error_on_empty_response():
    config = _config()
    logger = ExchangeLogger()

    with patch("pipeline.image_provider.OpenAI") as mock_openai_cls:
        mock_client = Mock()
        mock_client.images.generate.return_value = Mock(data=[])
        mock_openai_cls.return_value = mock_client
        result = fetch_source_image("a red bicycle", config, "fake-key", logger)

    assert result["used_fallback"] is True
    errors = [r["error"] for r in logger.records["image_provider"] if r["status"] == "error"]
    assert any("empty image response" in e for e in errors)
