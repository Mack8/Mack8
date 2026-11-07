#!/usr/bin/env python3
"""Draw a "Recently Active" card from the owner's public repositories.

Lists the repositories pushed most recently, with their main language and how
long ago they were touched. Only public repositories are read (the GitHub
users endpoint never returns private ones). The profile repository itself is
skipped because the workflows in this repo push to it every day.

The script fails loudly if the API call fails or returns nothing, so a broken
run never replaces the previous card with an empty one.

Usage: recent_activity_card.py <output.svg>
Environment: GITHUB_REPOSITORY_OWNER (default Mack8), GITHUB_TOKEN (optional)
"""
import html
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from palette import color_for, lighten  # noqa: E402

BG, ACCENT, TEXT = "#141321", "#fe428e", "#a9fef7"  # radical theme, same as the other cards
ROWS = 4


def fetch_repos(owner: str) -> list[dict]:
    url = f"https://api.github.com/users/{owner}/repos?type=owner&sort=pushed&direction=desc&per_page=30"
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "profile-card"}
    if os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as response:
        return json.load(response)


def when(moment: datetime, now: datetime) -> str:
    """Absolute date, so the card stays true no matter when it is viewed."""
    label = f"{moment.strftime('%b')} {moment.day}"
    return label if moment.year == now.year else f"{label}, {moment.year}"


def render(owner: str, repos: list[dict], now: datetime) -> str:
    used: dict = {}
    border, rule = lighten(BG, 0.12), lighten(BG, 0.07)
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="340" height="200" viewBox="0 0 340 200" role="img" aria-label="Recently active repositories">',
        "<style>text{font-family:'Segoe UI',Ubuntu,'Helvetica Neue',Sans-Serif}</style>",
        f'<rect x="1" y="1" width="338" height="198" rx="8" fill="{BG}" stroke="{border}" stroke-width="1"/>',
        f'<text x="24" y="38" font-size="20" fill="{ACCENT}">Recently Active</text>',
        f'<rect x="24" y="48" width="30" height="3" rx="1.5" fill="{ACCENT}"/>',
    ]
    for i, repo in enumerate(repos):
        y = 82 + i * 31
        name = repo["name"] if len(repo["name"]) <= 22 else repo["name"][:21] + "…"
        moment = datetime.fromisoformat(repo["pushed_at"].replace("Z", "+00:00"))
        color = color_for(repo.get("language") or "other", used)
        if i:
            parts.append(f'<line x1="24" y1="{y - 19}" x2="316" y2="{y - 19}" stroke="{rule}" stroke-width="1"/>')
        parts.append(f'<circle cx="31" cy="{y - 4}" r="5.5" fill="{color}"/>')
        parts.append(f'<text x="44" y="{y}" font-size="14" fill="{TEXT}">{html.escape(name)}</text>')
        parts.append(f'<text x="316" y="{y}" font-size="12" fill="{ACCENT}" text-anchor="end">{when(moment, now)}</text>')
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def main(output: str) -> None:
    owner = os.environ.get("GITHUB_REPOSITORY_OWNER", "Mack8")
    repos = [r for r in fetch_repos(owner) if r["name"].lower() != owner.lower() and not r["fork"] and not r["archived"] and not r["private"]]
    if not repos:
        raise SystemExit("no public repositories found; keeping the previous card")
    Path(output).write_text(render(owner, repos[:ROWS], datetime.now(timezone.utc)), encoding="utf-8")
    print(f"wrote {output} with {min(len(repos), ROWS)} repositories")


if __name__ == "__main__":
    main(sys.argv[1])
