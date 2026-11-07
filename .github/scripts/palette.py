"""Shared language palette for the profile charts.

The same language gets the same color in the two cards and in the ring inside
the 3D chart. The hues come from the heat-map palette used by the 3D bars.
"""

LANGUAGE_COLORS = {
    "typescript": "#3b82f6",
    "c#": "#22c55e",
    "python": "#facc15",
    "javascript": "#f97316",
    "other": "#64748b",
}
FALLBACK = ["#a855f7", "#14b8a6", "#ef4444", "#ec4899", "#06b6d4"]


def color_for(name: str, used: dict) -> str:
    """Stable color for a language name; unknown names take the next fallback."""
    key = name.strip().lower()
    if key in LANGUAGE_COLORS:
        return LANGUAGE_COLORS[key]
    if key not in used:
        used[key] = FALLBACK[len(used) % len(FALLBACK)]
    return used[key]


def label_color(fill: str) -> str:
    """Readable text color (dark or white) on top of a slice color."""
    h = fill.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))
    luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return "#0d1117" if luminance > 0.55 else "#ffffff"


def lighten(hex_color: str, amount: float) -> str:
    """Blend a color with white by the given amount (0 to 1)."""
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    mix = lambda c: round(c + (255 - c) * amount)
    return f"#{mix(r):02x}{mix(g):02x}{mix(b):02x}"
