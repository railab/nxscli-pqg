"""Private pyqtgraph animation lifecycle helpers."""

from typing import TYPE_CHECKING, Any

from PyQt6.QtCore import QTimer

if TYPE_CHECKING:
    from collections.abc import Callable


def has_frame_data(xdata: list[Any], ydata: list[Any]) -> bool:
    """Return whether an animation update has any frame data."""
    return any(len(series) > 0 for series in xdata) and any(
        len(series) > 0 for series in ydata
    )


def start_timer(
    callback: "Callable[[], None]",
    *,
    interval_ms: int = 10,
) -> QTimer:
    """Create and start a Qt timer for animation updates."""
    timer = QTimer()
    timer.timeout.connect(callback)
    timer.start(interval_ms)
    return timer


def stop_timer(timer: QTimer | None) -> None:
    """Stop a running timer if present."""
    if timer is not None:
        timer.stop()
