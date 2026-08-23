import json

from pipeline.archive import previously_used_links


def _write_metadata(archive_root, date_str, links):
    day_dir = archive_root / date_str
    day_dir.mkdir(parents=True)
    (day_dir / "metadata.json").write_text(
        json.dumps({"date": date_str, "headlines": [{"link": link} for link in links]}),
        encoding="utf-8",
    )


def test_previously_used_links_collects_links_across_all_days(tmp_path):
    archive_root = tmp_path / "archive"
    _write_metadata(archive_root, "2026-08-19", ["https://example.com/a"])
    _write_metadata(archive_root, "2026-08-20", ["https://example.com/b", "https://example.com/c"])

    links = previously_used_links(archive_root)
    assert links == {"https://example.com/a", "https://example.com/b", "https://example.com/c"}


def test_previously_used_links_respects_window_days(tmp_path):
    archive_root = tmp_path / "archive"
    _write_metadata(archive_root, "2026-08-18", ["https://example.com/old"])
    _write_metadata(archive_root, "2026-08-19", ["https://example.com/a"])
    _write_metadata(archive_root, "2026-08-20", ["https://example.com/b"])

    links = previously_used_links(archive_root, window_days=2)
    assert links == {"https://example.com/a", "https://example.com/b"}


def test_previously_used_links_ignores_days_without_headlines_or_metadata(tmp_path):
    archive_root = tmp_path / "archive"
    _write_metadata(archive_root, "2026-08-20", ["https://example.com/b"])
    (archive_root / "2026-08-21").mkdir(parents=True)  # no metadata.json at all

    links = previously_used_links(archive_root)
    assert links == {"https://example.com/b"}


def test_previously_used_links_returns_empty_set_when_archive_missing(tmp_path):
    assert previously_used_links(tmp_path / "does-not-exist") == set()
