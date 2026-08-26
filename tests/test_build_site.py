import json

from PIL import Image

from website.build_site import build


def _write_day(archive_root, date_str, *, with_share_card=False, concept_used_fallback=False, image_used_fallback=False):
    day_dir = archive_root / date_str
    day_dir.mkdir(parents=True)
    Image.new("RGB", (10, 10), color=(0, 0, 0)).save(day_dir / "final.png")
    (day_dir / "metadata.json").write_text(
        json.dumps({
            "date": date_str,
            "explanation": "test",
            "emotion": "joy",
            "emotion_color": "#d4a017",
            "concept_used_fallback": concept_used_fallback,
            "image_used_fallback": image_used_fallback,
        }),
        encoding="utf-8",
    )
    if with_share_card:
        Image.new("RGB", (10, 10), color=(255, 255, 255)).save(day_dir / "share_card.png")


def _write_week(oracle_archive_root, end_date_str, *, week_start=None, with_share_card=False, verdict="negative"):
    week_dir = oracle_archive_root / end_date_str
    week_dir.mkdir(parents=True)
    Image.new("RGB", (12, 8), color=(20, 10, 10)).save(week_dir / "final.png")
    (week_dir / "metadata.json").write_text(
        json.dumps({
            "week_start": week_start or end_date_str,
            "week_end": end_date_str,
            "concept": "test",
            "explanation": "test",
            "verdict": verdict,
            "verdict_color": "#5c1620" if verdict == "negative" else "#f3ead9",
            "concept_used_fallback": False,
            "image_used_fallback": False,
        }),
        encoding="utf-8",
    )
    if with_share_card:
        Image.new("RGB", (12, 8), color=(255, 255, 255)).save(week_dir / "share_card.png")


def _build(tmp_path, *, with_latest_share_card):
    archive_root = tmp_path / "archive"
    _write_day(archive_root, "2026-08-20", with_share_card=with_latest_share_card)
    _write_day(archive_root, "2026-08-19", with_share_card=False)

    config = {
        "site": {"title": "EMO", "base_url": "https://example.com/"},
        "paths": {
            "archive_dir": str(archive_root),
            "oracle_archive_dir": str(tmp_path / "oracle_archive"),
            "site_output_dir": str(tmp_path / "_site"),
        },
    }
    output_root = build(config)
    return output_root


def test_robots_txt_allows_all_and_points_at_sitemap(tmp_path):
    output_root = _build(tmp_path, with_latest_share_card=True)
    robots = (output_root / "robots.txt").read_text(encoding="utf-8")
    assert "User-agent: *" in robots
    assert "Allow: /" in robots
    assert "Sitemap: https://example.com/sitemap.xml" in robots


def test_sitemap_lists_home_archive_and_days_excluding_latest_duplicate(tmp_path):
    output_root = _build(tmp_path, with_latest_share_card=True)
    sitemap = (output_root / "sitemap.xml").read_text(encoding="utf-8")
    assert "<loc>https://example.com/</loc>" in sitemap
    assert "<loc>https://example.com/archive/</loc>" in sitemap
    assert "<loc>https://example.com/days/2026-08-19/</loc>" in sitemap
    # The latest day's page is a content duplicate of the homepage (see
    # build()'s canonical_url handling) and must not appear here too.
    assert "<loc>https://example.com/days/2026-08-20/</loc>" not in sitemap


def test_meta_description_and_og_title_always_present_even_without_share_card(tmp_path):
    output_root = _build(tmp_path, with_latest_share_card=False)
    older_day_html = (output_root / "days" / "2026-08-19" / "index.html").read_text(encoding="utf-8")
    assert '<meta name="description"' in older_day_html
    assert 'property="og:title"' in older_day_html
    assert 'property="og:description"' in older_day_html
    # No share_card.png for this day -> no image tags.
    assert 'property="og:image"' not in older_day_html
    assert 'name="twitter:image"' not in older_day_html


def test_og_image_present_when_share_card_exists(tmp_path):
    output_root = _build(tmp_path, with_latest_share_card=True)
    index_html = (output_root / "index.html").read_text(encoding="utf-8")
    assert '<meta property="og:image" content="https://example.com/days/2026-08-20/share_card.png">' in index_html


def test_latest_day_page_canonicalizes_to_homepage(tmp_path):
    output_root = _build(tmp_path, with_latest_share_card=True)
    latest_day_html = (output_root / "days" / "2026-08-20" / "index.html").read_text(encoding="utf-8")
    older_day_html = (output_root / "days" / "2026-08-19" / "index.html").read_text(encoding="utf-8")
    assert '<link rel="canonical" href="https://example.com/">' in latest_day_html
    assert '<link rel="canonical" href="https://example.com/days/2026-08-19/">' in older_day_html


def test_fallback_day_excluded_from_archive_grid_but_page_still_built(tmp_path):
    archive_root = tmp_path / "archive"
    _write_day(archive_root, "2026-08-20")
    _write_day(archive_root, "2026-08-19", concept_used_fallback=True)
    _write_day(archive_root, "2026-08-18", image_used_fallback=True)

    config = {
        "site": {"title": "EMO", "base_url": "https://example.com/"},
        "paths": {
            "archive_dir": str(archive_root),
            "oracle_archive_dir": str(tmp_path / "oracle_archive"),
            "site_output_dir": str(tmp_path / "_site"),
        },
    }
    output_root = build(config)

    archive_html = (output_root / "archive" / "index.html").read_text(encoding="utf-8")
    assert "2026-08-20" in archive_html
    assert "2026-08-19" not in archive_html
    assert "2026-08-18" not in archive_html

    # The fallback days' own pages must still exist and stay reachable,
    # and still be listed in the sitemap -- only the grid excludes them.
    assert (output_root / "days" / "2026-08-19" / "index.html").exists()
    assert (output_root / "days" / "2026-08-18" / "index.html").exists()
    sitemap = (output_root / "sitemap.xml").read_text(encoding="utf-8")
    assert "<loc>https://example.com/days/2026-08-19/</loc>" in sitemap
    assert "<loc>https://example.com/days/2026-08-18/</loc>" in sitemap


def _build_with_weeks(tmp_path, week_dates, **week_kwargs):
    archive_root = tmp_path / "archive"
    _write_day(archive_root, "2026-08-20")
    oracle_archive_root = tmp_path / "oracle_archive"
    for date_str in week_dates:
        _write_week(oracle_archive_root, date_str, **week_kwargs)

    config = {
        "site": {"title": "EMO", "base_url": "https://example.com/"},
        "paths": {
            "archive_dir": str(archive_root),
            "oracle_archive_dir": str(oracle_archive_root),
            "site_output_dir": str(tmp_path / "_site"),
        },
    }
    return build(config)


def test_oracle_pages_render_empty_state_when_no_weeks_archived(tmp_path):
    output_root = _build(tmp_path, with_latest_share_card=True)
    oracle_home = (output_root / "oracle" / "index.html").read_text(encoding="utf-8")
    assert "No ORACLE verdicts have been published yet." in oracle_home
    oracle_archive = (output_root / "oracle" / "archive" / "index.html").read_text(encoding="utf-8")
    assert "No ORACLE verdicts have been published yet." in oracle_archive
    assert not (output_root / "oracle" / "weeks").exists()


def test_oracle_home_page_shows_the_latest_week(tmp_path):
    output_root = _build_with_weeks(tmp_path, ["2026-08-19", "2026-08-26"], week_start="2026-08-20")
    oracle_home = (output_root / "oracle" / "index.html").read_text(encoding="utf-8")
    assert "2026-08-26" in oracle_home
    assert (output_root / "oracle" / "weeks" / "2026-08-26" / "final.png").exists()
    assert (output_root / "oracle" / "weeks" / "2026-08-19" / "final.png").exists()


def test_oracle_archive_labels_weeks_by_chronological_position_not_stored_counter(tmp_path):
    output_root = _build_with_weeks(tmp_path, ["2026-08-12", "2026-08-19", "2026-08-26"])
    archive_html = (output_root / "oracle" / "archive" / "index.html").read_text(encoding="utf-8")
    assert "WEEK 1" in archive_html  # oldest
    assert "WEEK 2" in archive_html
    assert "WEEK 3" in archive_html  # newest


def test_oracle_latest_week_page_canonicalizes_to_oracle_home(tmp_path):
    output_root = _build_with_weeks(tmp_path, ["2026-08-19", "2026-08-26"])
    latest_week_html = (output_root / "oracle" / "weeks" / "2026-08-26" / "index.html").read_text(encoding="utf-8")
    older_week_html = (output_root / "oracle" / "weeks" / "2026-08-19" / "index.html").read_text(encoding="utf-8")
    assert '<link rel="canonical" href="https://example.com/oracle/">' in latest_week_html
    assert '<link rel="canonical" href="https://example.com/oracle/weeks/2026-08-19/">' in older_week_html


def test_sitemap_and_robots_include_oracle_urls_excluding_latest_week_duplicate(tmp_path):
    output_root = _build_with_weeks(tmp_path, ["2026-08-19", "2026-08-26"])
    sitemap = (output_root / "sitemap.xml").read_text(encoding="utf-8")
    assert "<loc>https://example.com/oracle/</loc>" in sitemap
    assert "<loc>https://example.com/oracle/archive/</loc>" in sitemap
    assert "<loc>https://example.com/oracle/weeks/2026-08-19/</loc>" in sitemap
    assert "<loc>https://example.com/oracle/weeks/2026-08-26/</loc>" not in sitemap


def test_oracle_pages_load_oracle_stylesheet_and_dark_body_class(tmp_path):
    output_root = _build_with_weeks(tmp_path, ["2026-08-26"])
    oracle_home = (output_root / "oracle" / "index.html").read_text(encoding="utf-8")
    assert 'href="../static/oracle.css"' in oracle_home
    assert 'class="oracle-page"' in oracle_home
    # EMO's own homepage must stay unaffected.
    emo_home = (output_root / "index.html").read_text(encoding="utf-8")
    assert "oracle.css" not in emo_home
    assert 'class=""' in emo_home
