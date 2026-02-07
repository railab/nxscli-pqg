"""Private pyqtgraph format parsing helpers."""

from typing import Any

from PyQt6.QtCore import Qt

DEFAULT_COLORS = ["r", "g", "b", "c", "m", "y", "w"]

LINE_STYLES = {
    "-": Qt.PenStyle.SolidLine,
    "--": Qt.PenStyle.DashLine,
    "-.": Qt.PenStyle.DashDotLine,
    ":": Qt.PenStyle.DotLine,
}

MARKERS = {
    "o": "o",
    "s": "s",
    "t": "t",
    "t1": "t1",
    "t2": "t2",
    "t3": "t3",
    "d": "d",
    "+": "+",
    "x": "x",
    "p": "p",
    "h": "h",
    "star": "star",
}


def parse_format_string(fmt: str) -> dict[str, Any]:
    """Parse matplotlib-style format string."""
    result: dict[str, Any] = {
        "color": None,
        "linestyle": None,
        "marker": None,
    }
    if not fmt:
        return result

    original_fmt = fmt
    remaining = fmt
    colors = "rgbcmykw"
    if remaining and remaining[0] in colors:
        result["color"] = remaining[0]
        remaining = remaining[1:]

    if remaining.startswith("--"):
        result["linestyle"] = "--"
        remaining = remaining[2:]
    elif remaining.startswith("-."):
        result["linestyle"] = "-."
        remaining = remaining[2:]
    elif remaining.startswith(":"):
        result["linestyle"] = ":"
        remaining = remaining[1:]
    elif remaining.startswith("-"):
        result["linestyle"] = "-"
        remaining = remaining[1:]

    if remaining:
        if remaining in MARKERS:
            result["marker"] = remaining
        else:
            raise ValueError(
                f"Invalid format string '{original_fmt}': "
                f"unrecognized marker or character '{remaining}'.\n"
                f"Valid format: [color][linestyle][marker]\n"
                f"  Colors: {', '.join(colors)}\n"
                f"  Line styles: - (solid), -- (dashed), "
                f"-. (dash-dot), : (dotted)\n"
                f"  Markers: {', '.join(MARKERS.keys())}\n"
                f"Examples: 'r-', 'b--o', 'g:s', 'k-.+'"
            )

    if not any(result.values()):  # pragma: no cover
        raise ValueError(
            f"Invalid format string '{original_fmt}': "
            f"no valid color, line style, or marker found.\n"
            f"Valid format: [color][linestyle][marker]\n"
            f"  Colors: {', '.join(colors)}\n"
            f"  Line styles: - (solid), -- (dashed), "
            f"-. (dash-dot), : (dotted)\n"
            f"  Markers: {', '.join(MARKERS.keys())}\n"
            f"Examples: 'r-', 'b--o', 'g:s', 'k-.+'"
        )

    return result
