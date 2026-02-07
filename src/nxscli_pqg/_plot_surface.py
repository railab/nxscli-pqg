"""Private pyqtgraph plot-surface helpers."""

from typing import TYPE_CHECKING, Any

import pyqtgraph as pg  # type: ignore
from nxscli.logger import logger
from PyQt6.QtWidgets import QVBoxLayout, QWidget

if TYPE_CHECKING:
    from nxslib.dev import DeviceChannel

    from nxscli_pqg._plot_api import EPlotMode, PlotVectorState
    from nxscli_pqg._plot_data import PlotDataAxesPqg
    from nxscli_pqg.plot_pqg import PlotWindow


def numerical_channels(
    chanlist: list["DeviceChannel"],
) -> list["DeviceChannel"]:
    """Return numerical channels and log ignored ones."""
    newchanlist = []
    for chan in chanlist:
        if chan.data.is_numerical:
            newchanlist.append(chan)
        else:  # pragma: no cover
            logger.info(
                "NOTE: channel %d not numerical - ignore", chan.data.chan
            )
    return newchanlist


def expand_formats(
    chanlist: list["DeviceChannel"],
    fmt: list[str] | None = None,
) -> list[Any]:
    """Expand plot format arguments for all configured channels."""
    if not fmt:
        return [None for _ in range(len(chanlist))]
    if len(chanlist) != 1 and len(fmt) == 1:
        return [[fmt[0]] * chanlist[i].data.vdim for i in range(len(chanlist))]
    assert len(fmt) == len(
        chanlist
    ), "fmt must be specified for all configured channels"
    return fmt


def init_surface_widget(
    *,
    mode: "EPlotMode",
    dpi: float,
    parent: QWidget | None,
    window_factory: type["PlotWindow"],
) -> tuple["PlotWindow | None", QWidget, QVBoxLayout]:
    """Create the outer window/widget/layout for the plot surface."""
    window = None
    if mode.value == "detached":
        window = window_factory()
        window.setWindowTitle("NxScope Plot")
        window.resize(int(8 * dpi), int(6 * dpi))
        widget = QWidget()
        window.setCentralWidget(widget)
    else:
        widget = QWidget(parent)

    layout = QVBoxLayout(widget)
    layout.setContentsMargins(5, 5, 5, 5)
    layout.setSpacing(2)
    return window, widget, layout


def build_plot_widgets(
    channels: list["DeviceChannel"],
    layout: QVBoxLayout,
) -> list[pg.PlotWidget]:
    """Create plot widgets for numerical channels."""
    plot_widgets: list[pg.PlotWidget] = []
    for chan in channels:
        if chan.data.is_numerical:
            plot_widget = pg.PlotWidget()
            layout.addWidget(plot_widget)
            plot_widgets.append(plot_widget)
    return plot_widgets


def init_plot_data(
    chanlist: list["DeviceChannel"],
    plot_widgets: list[pg.PlotWidget],
    fmt: list[Any],
    plot_data_cls: type["PlotDataAxesPqg"],
) -> list["PlotDataAxesPqg"]:
    """Create plot-data objects for each numerical channel."""
    ret = []
    for i, channel in enumerate(chanlist):
        logger.info(
            "initialize PlotDataAxesPqg chan=%d vdim=%d fmt=%s",
            channel.data.chan,
            channel.data.vdim,
            fmt[i],
        )
        ret.append(plot_data_cls(plot_widgets[i], channel, fmt=fmt[i]))
    return ret


def get_vector_states(
    plist: list["PlotDataAxesPqg"],
    state_cls: type["PlotVectorState"],
) -> list["PlotVectorState"]:
    """Return current vector visibility state for all plots."""
    states: list["PlotVectorState"] = []
    for pdata in plist:
        for vector, curve in enumerate(pdata.curves):
            states.append(
                state_cls(
                    channel=pdata.chan,
                    vector=vector,
                    visible=bool(curve.isVisible()),
                )
            )
    return states


def set_vector_visible(
    plist: list["PlotDataAxesPqg"],
    *,
    channel: int,
    vector: int,
    visible: bool,
) -> None:
    """Set vector visibility for a channel/vector pair."""
    for pdata in plist:
        if pdata.chan != channel:
            continue
        if vector < 0 or vector >= len(pdata.curves):
            raise ValueError(
                f"Invalid vector index {vector} for channel {channel}"
            )
        pdata.curves[vector].setVisible(visible)
        return
    raise ValueError(f"Channel {channel} not found")
