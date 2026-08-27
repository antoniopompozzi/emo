"""Idempotenza di pipeline/main.py rispetto alla data odierna.

Con due trigger indipendenti sullo stesso workflow (Cloudflare Worker +
schedule: nativo come rete di sicurezza, vedi
infra/cloudflare-worker/README.md), la pipeline deve accorgersi da sola
se l'archivio del giorno esiste già e saltare la generazione, invece di
affidarsi solo alla guardia `if: github.event_name != 'push'` del
workflow (che copre un trigger diverso: i push di codice, non i trigger
duplicati dello stesso giorno)."""
import datetime as real_dt
import json
from unittest.mock import Mock

import pipeline.main as main_module

FIXED_DATE = "2026-08-27"


class _FrozenDateTime(real_dt.datetime):
    @classmethod
    def now(cls, tz=None):
        return real_dt.datetime(2026, 8, 27, 6, 3, tzinfo=real_dt.timezone.utc)


def _config(tmp_path):
    return {
        "news": {
            "primary_feed_url": "https://primary.example/rss",
            "fallback_feed_url": "https://fallback.example/rss",
            "max_items": 12,
            "request_timeout_seconds": 15,
            "dedup_window_days": 30,
        },
        "claude": {
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 1024,
            "request_timeout_seconds": 30,
            "max_retries": 3,
            "retry_backoff_seconds": 5,
        },
        "openai_image": {
            "model": "gpt-image-1.5",
            "quality": "medium",
            "size": "64x64",
            "request_timeout_seconds": 90,
            "max_retries": 4,
            "retry_backoff_seconds": 10,
        },
        "postprocess": {"grid_size": 4, "gray_levels": 4, "px_per_cell": 2},
        "site": {"title": "EMO", "base_url": "https://emopixels.xyz/"},
        "share_card": {"size": 64},
        "paths": {
            "archive_dir": str(tmp_path / "archive"),
            "site_output_dir": str(tmp_path / "_site"),
        },
    }


def _fake_headlines():
    return [{"title": "Headline", "summary": "Summary", "link": "https://example.com/1", "source": "bbc_world"}]


def test_run_generates_normally_when_todays_archive_is_absent(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(main_module, "load_config", lambda: _config(tmp_path))
    monkeypatch.setattr(main_module.dt, "datetime", _FrozenDateTime)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    fake_fetch = Mock(return_value=_fake_headlines())
    monkeypatch.setattr(main_module.news, "fetch_headlines", fake_fetch)

    day_dir = main_module.run()

    fake_fetch.assert_called_once()
    assert day_dir == tmp_path / "archive" / FIXED_DATE
    metadata = json.loads((day_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["date"] == FIXED_DATE
    assert metadata["concept_used_fallback"] is True
    assert metadata["image_used_fallback"] is True
    assert metadata["emotion"] == "neutral"
    assert "salto la generazione" not in capsys.readouterr().out


def test_run_skips_generation_when_todays_archive_already_exists(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(main_module, "load_config", lambda: _config(tmp_path))
    monkeypatch.setattr(main_module.dt, "datetime", _FrozenDateTime)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    day_dir = tmp_path / "archive" / FIXED_DATE
    day_dir.mkdir(parents=True)
    sentinel = {"date": FIXED_DATE, "sentinel": "already-here"}
    (day_dir / "metadata.json").write_text(json.dumps(sentinel), encoding="utf-8")

    fake_fetch = Mock(side_effect=AssertionError("fetch_headlines non deve essere chiamato quando si salta"))
    monkeypatch.setattr(main_module.news, "fetch_headlines", fake_fetch)

    result = main_module.run()

    fake_fetch.assert_not_called()
    assert result == day_dir
    assert json.loads((day_dir / "metadata.json").read_text(encoding="utf-8")) == sentinel
    out = capsys.readouterr().out
    assert "salto la generazione" in out
    assert FIXED_DATE in out


def test_daily_workflow_still_skips_pipeline_and_commit_steps_on_push():
    """Il guard `if: github.event_name != 'push'` in daily.yml resta la
    seconda protezione indipendente (push di codice, non trigger duplicati
    dello stesso giorno): questo test blocca una futura modifica accidentale
    che lo rimuova, dato che non è coperto da altri test Python."""
    workflow_path = main_module.REPO_ROOT / ".github" / "workflows" / "daily.yml"
    content = workflow_path.read_text(encoding="utf-8")
    assert content.count("if: github.event_name != 'push'") == 2
