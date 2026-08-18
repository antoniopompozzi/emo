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

    for day in days:
        day_source_dir = archive_root / day["_dir_name"]
        day_out_dir = output_root / "days" / day["_dir_name"]
        day_out_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(day_source_dir / "final.png", day_out_dir / "final.png")

        grid_values_path = day_source_dir / "grid_values.json"
        if grid_values_path.exists():
            shutil.copy(grid_values_path, day_out_dir / "grid_values.json")

    (output_root / "index.html").write_text(
        env.get_template("index.html").render(site_title=site_title, root="", today=days[0] if days else None),
        encoding="utf-8",
    )

    archive_out_dir = output_root / "archive"
    archive_out_dir.mkdir(parents=True, exist_ok=True)
    (archive_out_dir / "index.html").write_text(
        env.get_template("archive.html").render(site_title=site_title, root="../", days=days),
        encoding="utf-8",
    )

    day_template = env.get_template("day.html")
    for day in days:
        day_out_dir = output_root / "days" / day["_dir_name"]
        (day_out_dir / "index.html").write_text(
            day_template.render(site_title=site_title, root="../../", day=day),
            encoding="utf-8",
        )

    shutil.copytree(REPO_ROOT / "website" / "static", output_root / "static")

    # Tells GitHub Pages not to run this through Jekyll.
    (output_root / ".nojekyll").touch()

    return output_root


if __name__ == "__main__":
    out = build(load_config())
    print(f"Built site at {out}")
