import json

from PIL import Image

from website.build_site import build


def _write_day(archive_root, date_str, *, with_share_card=False):
    day_dir = archive_root / date_str
    day_dir.mkdir(parents=True)
    Image.new("RGB", (10, 10), color=(0, 0, 0)).save(day_dir / "final.png")
    (day_dir / "metadata.json").write_text(
        json.dumps({"date": date_str, "explanation": "test", "emotion": "joy", "emotion_color": "#d4a017"}),
        encoding="utf-8",
    )
    if with_share_card:
        Image.new("RGB", (10, 10), color=(255, 255, 255)).save(day_dir / "share_card.png")


def _build(tmp_path, *, with_latest_share_card):
    archive_root = tmp_path / "archive"
    _write_day(archive_root, "2026-08-20", with_share_card=with_latest_share_card)
    _write_day(archive_root, "2026-08-19", with_share_card=False)

    config = {
        "site": {"title": "EMO", "base_url": "https://example.com/"},
        "paths": {"archive_dir": str(archive_root), "site_output_dir": str(tmp_path / "_site")},
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
