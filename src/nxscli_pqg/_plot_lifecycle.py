"""Private pyqtgraph plot lifecycle helpers."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from PyQt6.QtWidgets import QWidget

    from nxscli_pqg._plot_data import PlotDataAxesPqg
    from nxscli_pqg.plot_pqg import PlotWindow


def clear_animations(ani: list[Any]) -> list[Any]:
    """Stop registered animations and return an empty list."""
    for item in ani:
        item.stop()
    return []


def clear_plot_data(plist: list["PlotDataAxesPqg"]) -> None:
    """Clear all rendered plot data."""
    for pdata in plist:  # pragma: no cover
        for curve in pdata.curves:
            curve.setData([], [])


def close_surface(
    window: "PlotWindow | None",
    widget: "QWidget",
    unregister_window: "Callable[[PlotWindow], None]",
) -> None:
    """Close a detached window or attached widget."""
    if window is not None:
        unregister_window(window)
        if window.isVisible():  # pragma: no cover
            window.close()
        return
    widget.close()
