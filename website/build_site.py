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
    # a different day" rather than a separate detail page/layout.
    # page_url (og:url) is always known -- it's just the route being
    # rendered -- and is passed on every page. share_url (og:image) is
    # only known when that day's share_card.png actually exists, so
    # og:title/og:description/meta-description still render on days
    # that predate the share feature; only the image tags are skipped.
    latest = days[0] if days else None
    latest_has_share_card = bool(latest) and (output_root / "days" / latest["_dir_name"] / "share_card.png").exists()
    (output_root / "index.html").write_text(
        env.get_template("index.html").render(
            site_title=site_title,
            root="",
            day=latest,
            image_base=f"days/{latest['_dir_name']}/" if latest else "",
            share_url=f"{base_url}days/{latest['_dir_name']}/share_card.png" if latest_has_share_card else None,
            page_url=base_url,
        ),
        encoding="utf-8",
    )

    archive_out_dir = output_root / "archive"
    archive_out_dir.mkdir(parents=True, exist_ok=True)
    (archive_out_dir / "index.html").write_text(
        env.get_template("archive.html").render(
            site_title=site_title, root="../", days=days, page_url=f"{base_url}archive/"
        ),
        encoding="utf-8",
    )

    day_template = env.get_template("day.html")
    for day in days:
        day_out_dir = output_root / "days" / day["_dir_name"]
        has_share_card = (day_out_dir / "share_card.png").exists()
        (day_out_dir / "index.html").write_text(
            day_template.render(
                site_title=site_title,
                root="../../",
                day=day,
                image_base="",
                share_url=f"{base_url}days/{day['_dir_name']}/share_card.png" if has_share_card else None,
                page_url=f"{base_url}days/{day['_dir_name']}/",
            ),
            encoding="utf-8",
        )

    shutil.copytree(REPO_ROOT / "website" / "static", output_root / "static")

    # Tells GitHub Pages not to run this through Jekyll.
    (output_root / ".nojekyll").touch()

    return output_root


if __name__ == "__main__":
    out = build(load_config())
    print(f"Built site at {out}")
