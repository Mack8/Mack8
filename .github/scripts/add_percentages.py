#!/usr/bin/env python3
"""Add a percentage next to each language in the donut cards.

The summary-cards action draws one arc per language but does not print the
share. The angle of each arc is the share, so it is derived from the path and
written into the legend. The script fails loudly if the SVG structure is not
what it expects, so a changed layout never publishes wrong numbers.

Usage: add_percentages.py <directory containing the card SVGs>
"""
import math
import re
import sys
from pathlib import Path

CARDS = ("1-repos-per-language.svg", "2-most-commit-language.svg")


def arc_share(d: str) -> float:
    """Share of the donut covered by one slice, from its outer arc."""
    m = re.match(
        r"M\s*([-\d.e]+),([-\d.e]+)\s*A\s*[-\d.e]+,[-\d.e]+,\d,\d,1,([-\d.e]+),([-\d.e]+)",
        d,
    )
    if not m:
        raise ValueError(f"unexpected path: {d[:80]}")
    x0, y0, x1, y1 = (float(v) for v in m.groups())
    start = math.atan2(x0, -y0) % math.tau
    end = math.atan2(x1, -y1) % math.tau
    return ((end - start) % math.tau) / math.tau


def label(share: float) -> str:
    pct = share * 100
    return "<1%" if pct < 1 else f"{pct:.0f}%"


def annotate(svg: str) -> str:
    accent = re.search(r'<text x="30" y="40"[^>]*fill: (#[0-9a-fA-F]{3,8})', svg)
    arcs = re.findall(
        r'<g class="arc" style="--gpsc-i: (\d+);">\s*<path d="([^"]+)" style="fill: (#[0-9a-fA-F]+)',
        svg,
    )
    rects = re.findall(
        r'<rect y="[\d.]+" width="14" height="14" class="gpsc-item" style="--gpsc-i: (\d+);[^"]*" fill="(#[0-9a-fA-F]+)"',
        svg,
    )
    texts = list(
        re.finditer(
            r'(<text x="16.8" y="[\d.]+" class="gpsc-item" style="--gpsc-i: (\d+);[^"]*">)((?:[^<]|<tspan[^>]*>[^<]*</tspan>)*)(</text>)',
            svg,
        )
    )
    if not (accent and arcs and len(arcs) == len(rects) == len(texts)):
        raise ValueError("card layout changed: arcs, legend swatches and labels do not match")

    shares = {}
    for idx, d, fill in arcs:
        swatch = dict(rects).get(idx)
        if swatch is None or swatch.lower() != fill.lower():
            raise ValueError(f"legend color {swatch} does not match arc color {fill} for slice {idx}")
        shares[idx] = arc_share(d) if len(arcs) > 1 else 1.0
    total = sum(shares.values())
    if not 0.98 <= total <= 1.02:
        raise ValueError(f"slice shares add up to {total:.3f}, expected 1")

    def repl(m: re.Match) -> str:
        name = m.group(3)
        if "<tspan" in name:
            return m.group(0)
        tag = f'<tspan dx="5" style="fill: {accent.group(1)}; font-size: 12px;">{label(shares[m.group(2)])}</tspan>'
        return f"{m.group(1)}{name}{tag}{m.group(4)}"

    return re.sub(texts[0].re.pattern, repl, svg)


def main(folder: str) -> None:
    for name in CARDS:
        path = Path(folder) / name
        path.write_text(annotate(path.read_text(encoding="utf-8")), encoding="utf-8")
        print(f"annotated {path}")


if __name__ == "__main__":
    main(sys.argv[1])
