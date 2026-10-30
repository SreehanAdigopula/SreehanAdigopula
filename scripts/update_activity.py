#!/usr/bin/env python3
"""Render a dependency-free profile dashboard using public GitHub metadata only."""

import argparse
from collections import Counter
from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
USERNAME = "SreehanAdigopula"
COLORS = {"JavaScript": "#e6c86e", "TypeScript": "#80b4e8", "Python": "#7dd3c7", "HTML": "#edaa8d", "CSS": "#b4a1e5"}


def fetch_repositories():
    repositories = []
    page = 1
    while True:
        # Deliberately unauthenticated: private repositories can never be included.
        url = f"https://api.github.com/users/{USERNAME}/repos?type=owner&per_page=100&page={page}"
        request = Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": f"{USERNAME}-profile"})
        with urlopen(request, timeout=30) as response:
            batch = json.load(response)
        if not isinstance(batch, list):
            raise ValueError("Expected a repository list from GitHub")
        repositories.extend(batch)
        if len(batch) < 100:
            return repositories
        page += 1


def text(x, y, value, size=14, color="#acbbc4", weight="400", extra=""):
    return f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" font-weight="{weight}" {extra}>{escape(str(value))}</text>'


def render(repositories, now=None):
    now = now or datetime.now(timezone.utc)
    public = [r for r in repositories if not r.get("private", False) and r.get("owner", {}).get("login", "").lower() == USERNAME.lower()]
    originals = [r for r in public if not r.get("fork")]
    projects = [r for r in originals if r["name"].lower() != USERNAME.lower() and not r.get("archived")]
    languages = Counter(r["language"] for r in projects if r.get("language"))
    recent = sorted([r for r in projects if r.get("pushed_at")], key=lambda r: r["pushed_at"], reverse=True)[:5]
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="680" viewBox="0 0 1100 680" role="img" aria-labelledby="title desc">',
             '<title id="title">Public GitHub activity</title>',
             f'<desc id="desc">{len(public)} public repositories, {len(originals)} original repositories, {len(languages)} primary languages. Snapshot {now:%Y-%m-%d} UTC. Recent repositories: {escape(", ".join(r["name"] for r in recent))}.</desc>',
             '<rect width="1100" height="680" rx="16" fill="#101b22"/>',
             '<g font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Arial,sans-serif">',
             text(36, 44, "FROM THE WORKSHOP", 13, "#7dd3c7", "600", 'letter-spacing="2"'),
             text(1064, 44, f"SNAPSHOT / {now:%Y-%m-%d} UTC", 12, extra='text-anchor="end" font-family="monospace"')]
    for x, number, label in [(36, len(public), "PUBLIC REPOSITORIES"), (394, len(originals), "ORIGINAL REPOSITORIES"), (752, len(languages), "PRIMARY LANGUAGES")]:
        parts.extend([f'<rect x="{x}" y="72" width="312" height="113" rx="9" fill="#18272f" stroke="#2d424c"/>', text(x+20, 126, number, 38, "#f1f0eb", "600"), text(x+20, 160, label, 11, "#acbbc4", "500", 'letter-spacing="1"')])
    parts.append(text(36, 229, "LANGUAGES ACROSS MY PROJECTS", 12, "#e6b779", "600", 'letter-spacing="1"'))
    parts.append(text(36, 255, "Primary language per original, non-archived project; profile repository excluded.", 13))
    x = 36
    total = sum(languages.values())
    for language, count in sorted(languages.items(), key=lambda item: (-item[1], item[0])):
        width = 1028 * count / total
        parts.append(f'<rect x="{x:.2f}" y="278" width="{width:.2f}" height="10" fill="{COLORS.get(language, "#8fa5b0")}"/>')
        x += width
    legend = sorted(languages.items(), key=lambda item: (-item[1], item[0]))
    for index, (language, count) in enumerate(legend[:6]):
        x, y = 36 + (index % 3) * 358, 320 + (index // 3) * 26
        parts.extend([f'<circle cx="{x+5}" cy="{y-5}" r="4" fill="{COLORS.get(language, "#8fa5b0")}"/>', text(x+20, y, f"{language} · {count} {'repo' if count == 1 else 'repos'}", 13)])
    parts.append('<path d="M36 373H1064" stroke="#2d424c"/>')
    parts.append(text(36, 409, "RECENTLY PUSHED", 12, "#e6b779", "600", 'letter-spacing="1"'))
    for index, repository in enumerate(recent):
        y = 450 + index * 39
        name = repository["name"]
        short_name = name if len(name) <= 42 else name[:39] + "…"
        parts.extend([text(36, y, f"0{index+1}", 12, "#7dd3c7", extra='font-family="monospace"'), text(78, y, short_name, 15, "#f1f0eb", "500"), text(750, y, repository.get("language") or "—", 13), text(1064, y, repository["pushed_at"][:10], 13, extra='text-anchor="end" font-family="monospace"')])
    parts.extend([text(36, 657, "PUBLIC DATA ONLY · UPDATED DAILY WITH GITHUB ACTIONS", 10, "#acbbc4", extra='letter-spacing="1"'), '</g></svg>'])
    return "\n".join(parts) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repos-json", type=Path, help="Use a saved public API response for local preview")
    args = parser.parse_args()
    repositories = json.loads(args.repos_json.read_text()) if args.repos_json else fetch_repositories()
    svg = render(repositories)
    destination = ROOT / "assets" / "activity.svg"
    destination.parent.mkdir(parents=True, exist_ok=True)
    # No changes are written until every API page has been fetched successfully.
    destination.write_text(svg)
    print(f"Updated {destination.relative_to(ROOT)} from public repository metadata")


if __name__ == "__main__":
    main()
