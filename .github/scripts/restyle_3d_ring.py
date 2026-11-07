#!/usr/bin/env python3
"""Recolor and label the language ring inside the 3D contribution chart.

The 3D generator draws a ring of commits per language but gives it neither a
title nor percentages, and colors it with GitHub's language colors. This script
recolors it with the shared palette, adds a title, writes the share of every
language in the legend (right-aligned column) and puts the top language in the
center, the same rule used by the language cards.

It fails loudly if the SVG is not what it expects.

Usage: restyle_3d_ring.py <chart.svg>
"""
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from palette import color_for, whole_percents  # noqa: E402

MARKER = "<!-- ring restyled -->"
RING_GROUP = '<g transform="translate(40, 520)">'

SLICE = re.compile(
    r'<path d="([^"]+)" style="fill: (#[0-9a-fA-F]{6});" class="stroke-bg" stroke-width="2px"><title>([^<]*?) (\d+)</title></path>'
)
SWATCH = re.compile(r'<rect x="0" y="([\d.]+)" width="([\d.]+)" height="[\d.]+" fill="(#[0-9a-fA-F]{6})" class="stroke-bg"')
LEGEND_TEXT = re.compile(r'(<text dominant-baseline="middle" x="26" y="([\d.]+)" class="fill-fg" font-size="([\d.]+)px">)([^<]+)(</text>)')


def point(radius: float, angle: float) -> tuple[float, float]:
    return radius * math.sin(angle), -radius * math.cos(angle)


def restyle(svg: str) -> str:
    start = svg.find(RING_GROUP)
    if start < 0:
        raise ValueError("ring group not found: the 3D layout changed")
    head, ring = svg[:start], svg[start:]

    slices = SLICE.findall(ring)
    if not slices:
        raise ValueError("no ring slices found")
    names = [s[2] for s in slices]
    counts = [int(s[3]) for s in slices]
    total = sum(counts)
    legend = LEGEND_TEXT.findall(ring)
    if [t[3] for t in legend] != names or len(SWATCH.findall(ring)) != len(names):
        raise ValueError("legend does not match the ring slices")

    outer = float(re.match(r"M[-\d.]+,([-\d.]+)A([\d.]+),", slices[0][0]).group(2))
    inner = float(re.search(r"L[-\d.]+,[-\d.]+A([\d.]+),", slices[0][0]).group(1))

    # consistency check: the first slice must end where the counts say it does
    a_end = counts[0] / total * math.tau
    ex, ey = point(outer, a_end)
    m = re.match(r"M[-\d.]+,[-\d.]+A[\d.]+,[\d.]+,\d,\d,1,([-\d.]+),([-\d.]+)", slices[0][0])
    if len(slices) > 1 and (abs(float(m.group(1)) - ex) > 1.5 or abs(float(m.group(2)) - ey) > 1.5):
        raise ValueError("slice geometry does not match the counts in the titles")

    used: dict = {}
    colors = {name: color_for(name, used) for name in names}
    originals = {s[1].lower(): colors[s[2]] for s in slices}

    # recolor swatches and slices (only inside the ring group)
    for orig, new in originals.items():
        ring = re.sub(rf'(<rect x="0" y="[\d.]+" width="[\d.]+" height="[\d.]+" fill=")({orig})(")', rf"\g<1>{new}\g<3>", ring, flags=re.I)
        ring = re.sub(rf'(<path d="[^"]+" style="fill: )({orig})(;")', rf"\g<1>{new}\g<3>", ring, flags=re.I)

    percents = whole_percents([c / total for c in counts])
    by_name = dict(zip(names, percents))
    top = max(range(len(names)), key=lambda i: counts[i])
    last = list(SLICE.finditer(ring))[-1]
    extras = (
        f'<text x="0" y="-4" font-size="34" font-weight="700" text-anchor="middle" class="fill-fg">{percents[top]}</text>'
        f'<text x="0" y="24" font-size="17" text-anchor="middle" class="fill-weak">{names[top]}</text>'
        f'<text x="0" y="{-outer - 20:.0f}" font-size="24" font-weight="600" text-anchor="middle" class="fill-fg">Languages by commits</text>'
    )
    ring = ring[: last.end()] + extras + ring[last.end() :]

    # the share of every language goes in a right-aligned column next to the legend
    def legend_repl(match: re.Match) -> str:
        name = match.group(4)
        value = (
            f'<text dominant-baseline="middle" x="215" y="{match.group(2)}" text-anchor="end" '
            f'class="fill-fg" font-size="{match.group(3)}px" font-weight="600">{by_name[name]}</text>'
        )
        return match.group(0) + value

    ring = LEGEND_TEXT.sub(legend_repl, ring)
    return head + ring.replace(RING_GROUP, RING_GROUP + MARKER, 1)


def main(path: str) -> None:
    file = Path(path)
    svg = file.read_text(encoding="utf-8")
    if MARKER in svg:
        print(f"already restyled {file}")
        return
    file.write_text(restyle(svg), encoding="utf-8")
    print(f"restyled {file}")


if __name__ == "__main__":
    main(sys.argv[1])
