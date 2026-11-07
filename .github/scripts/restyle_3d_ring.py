#!/usr/bin/env python3
"""Recolor and label the language ring inside the 3D contribution chart.

The 3D generator draws a ring of commits per language but gives it neither a
title nor percentages, and colors it with GitHub's language colors. This script
recolors it with the shared palette, writes the share on each slice, adds a
title and appends the share to the legend entries of thin slices.

It fails loudly if the SVG is not what it expects.

Usage: restyle_3d_ring.py <chart.svg>
"""
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from palette import color_for, label_color  # noqa: E402

MARKER = "<!-- ring restyled -->"
MIN_LABEL_SHARE = 0.06
RING_GROUP = '<g transform="translate(40, 520)">'

SLICE = re.compile(
    r'<path d="([^"]+)" style="fill: (#[0-9a-fA-F]{6});" class="stroke-bg" stroke-width="2px"><title>([^<]*?) (\d+)</title></path>'
)
SWATCH = re.compile(r'<rect x="0" y="([\d.]+)" width="([\d.]+)" height="[\d.]+" fill="(#[0-9a-fA-F]{6})" class="stroke-bg"')
LEGEND_TEXT = re.compile(r'(<text dominant-baseline="middle" x="26" y="[\d.]+" class="fill-fg" font-size="[\d.]+px">)([^<]+)(</text>)')


def pct(share: float) -> str:
    return "<1%" if share * 100 < 1 else f"{share * 100:.0f}%"


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
    if [t[1] for t in legend] != names or len(SWATCH.findall(ring)) != len(names):
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

    # percentage on each slice, drawn right after the last slice path
    labels, angle = [], 0.0
    for name, count in zip(names, counts):
        nxt = angle + count / total * math.tau
        if count / total >= MIN_LABEL_SHARE:
            x, y = point((outer + inner) / 2, (angle + nxt) / 2)
            labels.append(
                f'<text x="{x:.1f}" y="{y:.1f}" font-size="24" font-weight="700" fill="{label_color(colors[name])}" '
                f'text-anchor="middle" dominant-baseline="central">{pct(count / total)}</text>'
            )
        angle = nxt
    last = list(SLICE.finditer(ring))[-1]
    title = (
        f'<text x="0" y="{-outer - 20:.0f}" font-size="24" font-weight="600" text-anchor="middle" '
        f'class="fill-fg">Languages by commits</text>'
    )
    ring = ring[: last.end()] + "".join(labels) + title + ring[last.end() :]

    # thin slices get their share in the legend
    def legend_repl(match: re.Match) -> str:
        name = match.group(2)
        share = counts[names.index(name)] / total
        if share >= MIN_LABEL_SHARE:
            return match.group(0)
        return f'{match.group(1)}{name}<tspan dx="8" fill="#8b949e">{pct(share)}</tspan>{match.group(3)}'

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
