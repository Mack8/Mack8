#!/usr/bin/env python3
"""Redraw the two language donut cards with the share inside the ring.

The summary-cards action draws one arc per language but prints no share. The
angle of each arc is the share, so this script reads names, colors and shares
from the generated SVG and writes a new card: a thicker ring with the percentage
on each slice, the top language in the center and a tidy legend.

It fails loudly if the generated SVG is not what it expects, so a changed
layout never publishes wrong numbers.

Usage: restyle_language_cards.py <directory containing the card SVGs>
"""
import math
import re
import sys
from pathlib import Path

CARDS = ("1-repos-per-language.svg", "2-most-commit-language.svg")
MARKER = "<!-- restyled -->"
CX, CY, R_OUT, R_IN = 252, 118, 64, 40
MIN_LABEL_SHARE = 0.07


def arc_share(d: str) -> float:
    """Share of the donut covered by one slice, from its outer arc."""
    m = re.match(
        r"M\s*([-\d.e]+),([-\d.e]+)\s*A\s*[-\d.e]+,[-\d.e]+,\d,\d,1,([-\d.e]+),([-\d.e]+)", d
    )
    if not m:
        raise ValueError(f"unexpected path: {d[:80]}")
    x0, y0, x1, y1 = (float(v) for v in m.groups())
    start = math.atan2(x0, -y0) % math.tau
    end = math.atan2(x1, -y1) % math.tau
    return ((end - start) % math.tau) / math.tau


def lighten(hex_color: str, amount: float) -> str:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    mix = lambda c: round(c + (255 - c) * amount)
    return f"#{mix(r):02x}{mix(g):02x}{mix(b):02x}"


def parse(svg: str) -> dict:
    title = re.search(
        r'<text x="30" y="40"[^>]*?fill: (#[0-9a-fA-F]{3,8})[^>]*>([^<]*)</text>', svg
    )
    bg = re.search(r'<rect x="1" y="1"[^>]*\sfill="(#[0-9a-fA-F]{3,8})"', svg)
    arcs = re.findall(
        r'<g class="arc" style="--gpsc-i: (\d+);">\s*<path d="([^"]+)" style="fill: (#[0-9a-fA-F]+)', svg
    )
    rects = dict(
        re.findall(
            r'<rect y="[\d.]+" width="14" height="14" class="gpsc-item" style="--gpsc-i: (\d+);[^"]*" fill="(#[0-9a-fA-F]+)"',
            svg,
        )
    )
    texts = re.findall(
        r'<text x="16.8" y="[\d.]+" class="gpsc-item" style="--gpsc-i: (\d+);[^"]*fill: (#[0-9a-fA-F]+)[^"]*">((?:[^<]|<tspan[^>]*>[^<]*</tspan>)*)</text>',
        svg,
    )
    if not (title and bg and arcs and len(arcs) == len(rects) == len(texts)):
        raise ValueError("card layout changed: arcs, legend swatches and labels do not match")

    names = {i: re.sub(r"<[^>]+>", "", re.sub(r"<tspan[^>]*>[^<]*</tspan>", "", t)).strip() for i, _, t in texts}
    text_color = texts[0][1]
    slices = []
    for idx, d, fill in arcs:
        if rects.get(idx, "").lower() != fill.lower():
            raise ValueError(f"legend color does not match arc color for slice {idx}")
        share = arc_share(d) if len(arcs) > 1 else 1.0
        slices.append({"name": names[idx], "color": fill, "share": share})
    total = sum(s["share"] for s in slices)
    if not 0.98 <= total <= 1.02:
        raise ValueError(f"slice shares add up to {total:.3f}, expected 1")
    return {
        "title": title.group(2).strip(),
        "accent": title.group(1),
        "bg": bg.group(1),
        "text": text_color,
        "slices": slices,
    }


def point(radius: float, angle: float) -> tuple[float, float]:
    return CX + radius * math.sin(angle), CY - radius * math.cos(angle)


def slice_path(a0: float, a1: float) -> str:
    large = 1 if a1 - a0 > math.pi else 0
    ox0, oy0 = point(R_OUT, a0)
    ox1, oy1 = point(R_OUT, a1)
    ix1, iy1 = point(R_IN, a1)
    ix0, iy0 = point(R_IN, a0)
    return (
        f"M{ox0:.2f},{oy0:.2f}A{R_OUT},{R_OUT},0,{large},1,{ox1:.2f},{oy1:.2f}"
        f"L{ix1:.2f},{iy1:.2f}A{R_IN},{R_IN},0,{large},0,{ix0:.2f},{iy0:.2f}Z"
    )


def pct(share: float) -> str:
    return "<1%" if share * 100 < 1 else f"{share * 100:.0f}%"


def render(card: dict) -> str:
    slices, bg = card["slices"], card["bg"]
    border = lighten(bg, 0.12)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="340" height="200" viewBox="0 0 340 200" role="img" aria-label="{card["title"]}">',
        MARKER,
        "<style>text{font-family:'Segoe UI',Ubuntu,'Helvetica Neue',Sans-Serif}</style>",
        f'<rect x="1" y="1" width="338" height="198" rx="8" fill="{bg}" stroke="{border}" stroke-width="1"/>',
        f'<text x="24" y="38" font-size="20" fill="{card["accent"]}">{card["title"]}</text>',
        f'<rect x="24" y="48" width="30" height="3" rx="1.5" fill="{card["accent"]}"/>',
    ]

    gap = min(26.0, 120.0 / len(slices))
    y0 = CY - (len(slices) - 1) * gap / 2
    for i, s in enumerate(slices):
        y = y0 + i * gap
        parts.append(f'<circle cx="31" cy="{y:.1f}" r="5.5" fill="{s["color"]}"/>')
        label = s["name"]
        extra = ""
        if s["share"] < MIN_LABEL_SHARE and len(slices) > 1:
            extra = f'<tspan dx="6" font-size="12" fill="{card["accent"]}">{pct(s["share"])}</tspan>'
        parts.append(f'<text x="44" y="{y + 5:.1f}" font-size="14" fill="{card["text"]}">{label}{extra}</text>')

    if len(slices) == 1:
        s = slices[0]
        mid = (R_OUT + R_IN) / 2
        parts.append(
            f'<circle cx="{CX}" cy="{CY}" r="{mid}" fill="none" stroke="{s["color"]}" stroke-width="{R_OUT - R_IN}"/>'
        )
    else:
        angle = 0.0
        for s in slices:
            a1 = angle + s["share"] * math.tau
            parts.append(
                f'<path d="{slice_path(angle, a1)}" fill="{s["color"]}" stroke="{bg}" stroke-width="2.5" stroke-linejoin="round"/>'
            )
            if s["share"] >= MIN_LABEL_SHARE:
                lx, ly = point((R_OUT + R_IN) / 2, (angle + a1) / 2)
                parts.append(
                    f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="11" font-weight="700" fill="#ffffff" text-anchor="middle" dominant-baseline="central">{pct(s["share"])}</text>'
                )
            angle = a1

    top = max(slices, key=lambda s: s["share"])
    parts.append(
        f'<text x="{CX}" y="{CY - 2}" font-size="17" font-weight="700" fill="#ffffff" text-anchor="middle">{pct(top["share"])}</text>'
    )
    parts.append(
        f'<text x="{CX}" y="{CY + 13}" font-size="9.5" fill="{card["text"]}" text-anchor="middle">{top["name"]}</text>'
    )
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def main(folder: str) -> None:
    for name in CARDS:
        path = Path(folder) / name
        svg = path.read_text(encoding="utf-8")
        if MARKER in svg:
            print(f"already restyled {path}")
            continue
        path.write_text(render(parse(svg)), encoding="utf-8")
        print(f"restyled {path}")


if __name__ == "__main__":
    main(sys.argv[1])
