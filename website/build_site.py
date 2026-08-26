"""Builds EMO's static site from the archive/ directory.

Run as: python website/build_site.py

Reads every archive/<date>/metadata.json, copies the corresponding
final.png, and renders the Jinja2 templates in website/templates/ into
a self-contained output directory ready to be published (default:
_site/, see config.yaml -> paths.site_output_dir).
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

REPO_ROOT = Path(__file__).resolve().parent.parent


def load_config() -> dict:
    with open(REPO_ROOT / "config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def is_fallback_day(day: dict) -> bool:
    return bool(day.get("concept_used_fallback")) or bool(day.get("image_used_fallback"))


def load_days(archive_root: Path) -> list[dict]:
    days = []
    if not archive_root.exists():
        return days
    for day_dir in sorted(archive_root.iterdir(), key=lambda p: p.name, reverse=True):
        metadata_path = day_dir / "metadata.json"
        if not day_dir.is_dir() or not metadata_path.exists():
            continue
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata["_dir_name"] = day_dir.name
        days.append(metadata)
    return days


def load_weeks(oracle_archive_root: Path) -> list[dict]:
    weeks = []
    if not oracle_archive_root.exists():
        return weeks
    for week_dir in sorted(oracle_archive_root.iterdir(), key=lambda p: p.name, reverse=True):
        metadata_path = week_dir / "metadata.json"
        if not week_dir.is_dir() or not metadata_path.exists():
            continue
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata["_dir_name"] = week_dir.name
        weeks.append(metadata)
    return weeks


def write_robots_and_sitemap(output_root: Path, base_url: str, days: list[dict], weeks: list[dict]) -> None:
    (output_root / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\n\nSitemap: {base_url}sitemap.xml\n",
        encoding="utf-8",
    )

    # The latest day's own /days/<date>/ page renders identical content
    # to the homepage (see the comment in build() about _hero.html) and
    # is marked canonical to the homepage there, so it's left out of the
    # sitemap to avoid asking search engines to index the same content
    # twice under two URLs. Same reasoning for ORACLE's latest week vs.
    # oracle/index.html.
    latest_dir_name = days[0]["_dir_name"] if days else None
    day_urls = [f"{base_url}days/{day['_dir_name']}/" for day in days if day["_dir_name"] != latest_dir_name]

    latest_week_dir_name = weeks[0]["_dir_name"] if weeks else None
    week_urls = [
        f"{base_url}oracle/weeks/{week['_dir_name']}/" for week in weeks if week["_dir_name"] != latest_week_dir_name
    ]

    urls = [base_url, f"{base_url}archive/"] + day_urls
    urls += [f"{base_url}oracle/", f"{base_url}oracle/archive/"] + week_urls
    body = "\n".join(f"  <url><loc>{url}</loc></url>" for url in urls)
    sitemap = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{body}\n"
        "</urlset>\n"
    )
    (output_root / "sitemap.xml").write_text(sitemap, encoding="utf-8")


def build(config: dict) -> Path:
    archive_root = REPO_ROOT / config["paths"]["archive_dir"]
    output_root = REPO_ROOT / config["paths"]["site_output_dir"]

    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True)

    days = load_days(archive_root)

    env = Environment(
        loader=FileSystemLoader(REPO_ROOT / "website" / "templates"),
        autoescape=select_autoescape(["html"]),
    )
    site_title = config["site"]["title"]
    base_url = config["site"]["base_url"]

    # grid_values.json stays in archive/ (it's still written by the
    # pipeline as raw data for the thesis writeup) but the site itself
    # just shows final.png directly, so it isn't copied into _site/.
    # share_card.png doesn't exist for days archived before the share
    # feature was added, so it's copied (and og:image/twitter:image
    # emitted) only when present -- older days just render without them.
    for day in days:
        day_source_dir = archive_root / day["_dir_name"]
        day_out_dir = output_root / "days" / day["_dir_name"]
        day_out_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(day_source_dir / "final.png", day_out_dir / "final.png")
        share_card_source = day_source_dir / "share_card.png"
        if share_card_source.exists():
            shutil.copy(share_card_source, day_out_dir / "share_card.png")

    # index.html and days/<date>/index.html both render the exact same
    # _hero.html partial (see that file's header comment) -- the only
    # difference is which day's data/assets get passed in. This is what
    # makes clicking an archive thumbnail land on "the homepage, showing
    # a different day" rather than a separate detail page/layout. Since
    # the two pages are literally identical content, the latest day's
    # own page sets canonical_url to the homepage instead of itself, so
    # search engines treat the homepage as the one indexable copy.
    # page_url (og:url) is always known -- it's just the route being
    # rendered -- and is passed on every page. share_url (og:image) is
    # only known when that day's share_card.png actually exists, so
    # og:title/og:description/meta-description still render on days
    # that predate the share feature; only the image tags are skipped.
    latest = days[0] if days else None
    latest_dir_name = latest["_dir_name"] if latest else None
    latest_has_share_card = bool(latest) and (output_root / "days" / latest_dir_name / "share_card.png").exists()
    (output_root / "index.html").write_text(
        env.get_template("index.html").render(
            site_title=site_title,
            root="",
            day=latest,
            image_base=f"days/{latest_dir_name}/" if latest else "",
            share_url=f"{base_url}days/{latest_dir_name}/share_card.png" if latest_has_share_card else None,
            page_url=base_url,
            canonical_url=base_url,
        ),
        encoding="utf-8",
    )

    # Fallback days (concept_used_fallback or image_used_fallback) are
    # left out of the archive grid's thumbnails -- the day's own content
    # was degraded that day, so it's not representative of what EMO
    # produced from the news. Their own /days/<date>/ page is still built
    # below like any other day, disclosing the fallback in its "why this
    # image?" modal (_hero.html) as always; only the grid listing skips
    # them, so this file remains unreachable through the archive index
    # but stays a normal, linkable page.
    archive_out_dir = output_root / "archive"
    archive_out_dir.mkdir(parents=True, exist_ok=True)
    gallery_days = [day for day in days if not is_fallback_day(day)]
    (archive_out_dir / "index.html").write_text(
        env.get_template("archive.html").render(
            site_title=site_title,
            root="../",
            days=gallery_days,
            page_url=f"{base_url}archive/",
            canonical_url=f"{base_url}archive/",
        ),
        encoding="utf-8",
    )

    day_template = env.get_template("day.html")
    for day in days:
        day_out_dir = output_root / "days" / day["_dir_name"]
        has_share_card = (day_out_dir / "share_card.png").exists()
        day_url = f"{base_url}days/{day['_dir_name']}/"
        (day_out_dir / "index.html").write_text(
            day_template.render(
                site_title=site_title,
                root="../../",
                day=day,
                image_base="",
                share_url=f"{base_url}days/{day['_dir_name']}/share_card.png" if has_share_card else None,
                page_url=day_url,
                canonical_url=base_url if day["_dir_name"] == latest_dir_name else day_url,
            ),
            encoding="utf-8",
        )

    # ORACLE: same "shared _hero partial, differ only by which day's
    # data/assets get passed in" pattern as index.html/day.html above,
    # via oracle.html/oracle_week.html and _oracle_hero.html -- built
    # from a separate root (oracle_archive/) into a separate output
    # subtree (oracle/), with no change to how days/archive/ are built.
    oracle_archive_root = REPO_ROOT / config["paths"]["oracle_archive_dir"]
    weeks = load_weeks(oracle_archive_root)

    for week in weeks:
        week_source_dir = oracle_archive_root / week["_dir_name"]
        week_out_dir = output_root / "oracle" / "weeks" / week["_dir_name"]
        week_out_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(week_source_dir / "final.png", week_out_dir / "final.png")
        week_share_card_source = week_source_dir / "share_card.png"
        if week_share_card_source.exists():
            shutil.copy(week_share_card_source, week_out_dir / "share_card.png")

    # WEEK N is the week's position in chronological order (oldest = 1),
    # computed here rather than stored in metadata.json, since it shifts
    # whenever an even older week is later added to the archive.
    for position, week in enumerate(reversed(weeks), start=1):
        week["week_number"] = position

    oracle_out_dir = output_root / "oracle"
    oracle_out_dir.mkdir(parents=True, exist_ok=True)

    latest_week = weeks[0] if weeks else None
    latest_week_dir_name = latest_week["_dir_name"] if latest_week else None
    latest_week_has_share_card = bool(latest_week) and (
        output_root / "oracle" / "weeks" / latest_week_dir_name / "share_card.png"
    ).exists()
    (oracle_out_dir / "index.html").write_text(
        env.get_template("oracle.html").render(
            site_title=site_title,
            root="../",
            oracle_root="",
            week=latest_week,
            image_base=f"weeks/{latest_week_dir_name}/" if latest_week else "",
            share_url=f"{base_url}oracle/weeks/{latest_week_dir_name}/share_card.png"
            if latest_week_has_share_card
            else None,
            page_url=f"{base_url}oracle/",
            canonical_url=f"{base_url}oracle/",
        ),
        encoding="utf-8",
    )

    oracle_archive_out_dir = oracle_out_dir / "archive"
    oracle_archive_out_dir.mkdir(parents=True, exist_ok=True)
    (oracle_archive_out_dir / "index.html").write_text(
        env.get_template("oracle_archive.html").render(
            site_title=site_title,
            root="../../",
            oracle_root="../",
            weeks=weeks,
            page_url=f"{base_url}oracle/archive/",
            canonical_url=f"{base_url}oracle/archive/",
        ),
        encoding="utf-8",
    )

    oracle_week_template = env.get_template("oracle_week.html")
    for week in weeks:
        week_out_dir = output_root / "oracle" / "weeks" / week["_dir_name"]
        has_share_card = (week_out_dir / "share_card.png").exists()
        week_url = f"{base_url}oracle/weeks/{week['_dir_name']}/"
        (week_out_dir / "index.html").write_text(
            oracle_week_template.render(
                site_title=site_title,
                root="../../../",
                oracle_root="../../",
                week=week,
                image_base="",
                share_url=f"{base_url}oracle/weeks/{week['_dir_name']}/share_card.png" if has_share_card else None,
                page_url=week_url,
                canonical_url=f"{base_url}oracle/" if week["_dir_name"] == latest_week_dir_name else week_url,
            ),
            encoding="utf-8",
        )

    shutil.copytree(REPO_ROOT / "website" / "static", output_root / "static")

    write_robots_and_sitemap(output_root, base_url, days, weeks)

    # Tells GitHub Pages not to run this through Jekyll.
    (output_root / ".nojekyll").touch()

    return output_root


if __name__ == "__main__":
    out = build(load_config())
    print(f"Built site at {out}")
