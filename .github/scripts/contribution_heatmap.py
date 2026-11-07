#!/usr/bin/env python3
"""Draw a flat contribution heatmap card from the owner's contribution calendar.

Reads the last year of daily contributions from the GitHub GraphQL API and
draws one square per day, in the same card style and heat palette as the other
cards, with a few figures that are computed from the same data (total, active
days, longest streak).

The script fails loudly if the API call fails, returns no weeks, or the daily
counts do not add up to the reported total, so a broken run never replaces the
previous card with wrong numbers.

Usage: contribution_heatmap.py <output.svg>
Environment: GITHUB_TOKEN (required), GITHUB_REPOSITORY_OWNER (default Mack8)
"""
import json
import os
import sys
import urllib.request
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from palette import lighten  # noqa: E402

BG, ACCENT, TEXT, MUTED = "#141321", "#fe428e", "#a9fef7", "#8b949e"
LEVEL_COLORS = ["#1e293b", "#3b82f6", "#22c55e", "#facc15", "#ef4444"]
LEVELS = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}
CELL, PITCH = 14, 17
LEFT, TOP = 62, 98
QUERY = """query($login: String!) { user(login: $login) { contributionsCollection { contributionCalendar {
  totalContributions weeks { firstDay contributionDays { date contributionCount contributionLevel weekday } } } } } }"""


def fetch(owner: str, token: str) -> dict:
    body = json.dumps({"query": QUERY, "variables": {"login": owner}}).encode()
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json", "User-Agent": "profile-card"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    if payload.get("errors") or not payload.get("data", {}).get("user"):
        raise SystemExit(f"GraphQL error: {payload.get('errors')}")
    return payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def longest_streak(counts: list[int]) -> int:
    best = run = 0
    for count in counts:
        run = run + 1 if count > 0 else 0
        best = max(best, run)
    return best


def render(calendar: dict) -> str:
    weeks = calendar["weeks"]
    days = [d for w in weeks for d in w["contributionDays"]]
    counts = [d["contributionCount"] for d in days]
    if not weeks or sum(counts) != calendar["totalContributions"]:
        raise SystemExit("daily counts do not add up to the reported total; keeping the previous card")

    width = LEFT + len(weeks) * PITCH + 24
    grid_bottom = TOP + 7 * PITCH
    height = grid_bottom + 52
    border = lighten(BG, 0.12)
    active = sum(1 for c in counts if c > 0)
    streak = longest_streak(counts)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Contributions in the last year">',
        "<style>text{font-family:'Segoe UI',Ubuntu,'Helvetica Neue',Sans-Serif}</style>",
        f'<rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="8" fill="{BG}" stroke="{border}" stroke-width="1"/>',
        f'<text x="24" y="38" font-size="20" fill="{ACCENT}">Contributions in the last year</text>',
        f'<rect x="24" y="48" width="30" height="3" rx="1.5" fill="{ACCENT}"/>',
        f'<text x="{width - 24}" y="36" font-size="15" fill="{TEXT}" text-anchor="end">'
        f'<tspan font-weight="700" fill="#ffffff">{calendar["totalContributions"]:,}</tspan> contributions'
        f'<tspan dx="18" font-weight="700" fill="#ffffff">{active}</tspan> active days'
        f'<tspan dx="18" font-weight="700" fill="#ffffff">{streak}</tspan>-day best streak</text>',
    ]

    last_label = -10
    previous_month = None
    for i, week in enumerate(weeks):
        month = date.fromisoformat(week["firstDay"]).month
        if month != previous_month and i - last_label >= 3 and i <= len(weeks) - 3:
            name = date.fromisoformat(week["firstDay"]).strftime("%b")
            parts.append(f'<text x="{LEFT + i * PITCH}" y="{TOP - 10}" font-size="13" fill="{MUTED}">{name}</text>')
            last_label = i
        previous_month = month

    for row, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        parts.append(f'<text x="24" y="{TOP + row * PITCH + 12}" font-size="12" fill="{MUTED}">{name}</text>')

    for i, week in enumerate(weeks):
        for day in week["contributionDays"]:
            level = LEVELS[day["contributionLevel"]]
            when = date.fromisoformat(day["date"])
            label = f"{day['contributionCount']} contributions on {when.strftime('%b')} {when.day}, {when.year}"
            parts.append(
                f'<rect x="{LEFT + i * PITCH}" y="{TOP + day["weekday"] * PITCH}" width="{CELL}" height="{CELL}" rx="3" fill="{LEVEL_COLORS[level]}">'
                f"<title>{label}</title></rect>"
            )

    legend_y = grid_bottom + 18
    x = width - 24 - 5 * PITCH - 36
    parts.append(f'<text x="{x - 8}" y="{legend_y + 11}" font-size="12" fill="{MUTED}" text-anchor="end">Less</text>')
    for level, color in enumerate(LEVEL_COLORS):
        parts.append(f'<rect x="{x + level * PITCH}" y="{legend_y}" width="{CELL}" height="{CELL}" rx="3" fill="{color}"/>')
    parts.append(f'<text x="{x + 5 * PITCH + 4}" y="{legend_y + 11}" font-size="12" fill="{MUTED}">More</text>')
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def main(output: str) -> None:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN is required")
    calendar = fetch(os.environ.get("GITHUB_REPOSITORY_OWNER", "Mack8"), token)
    Path(output).write_text(render(calendar), encoding="utf-8")
    print(f"wrote {output} ({calendar['totalContributions']} contributions)")


if __name__ == "__main__":
    main(sys.argv[1])
