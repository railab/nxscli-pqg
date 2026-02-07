"""The pyqtgraph plot specific module."""

from typing import TYPE_CHECKING, Any

import pyqtgraph as pg  # type: ignore
from nxscli.idata import PluginData, PluginDataCb, PluginQueueData
from nxscli.logger import logger
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QMainWindow, QWidget

from nxscli_pqg._animation_common import (
    fetch_animation_data,
    flush_chunks,
    init_xy_buffers,
)
from nxscli_pqg._animation_lifecycle import (
    has_frame_data,
    start_timer,
    stop_timer,
)
from nxscli_pqg._plot_api import EPlotMode, PlotVectorState
from nxscli_pqg._plot_constants import DEFAULT_DPI, LIVE_TIMER_INTERVAL_MS
from nxscli_pqg._plot_data import PlotDataAxesPqg, PlotDataCommon
from nxscli_pqg._plot_factory import create_plot_surface
from nxscli_pqg._plot_format import (
    DEFAULT_COLORS,
    LINE_STYLES,
    MARKERS,
    parse_format_string,
)
from nxscli_pqg._plot_lifecycle import (
    clear_animations as clear_plot_animations,
)
from nxscli_pqg._plot_lifecycle import (
    clear_plot_data,
    close_surface,
)
from nxscli_pqg._plot_surface import (
    build_plot_widgets,
    expand_formats,
)
from nxscli_pqg._plot_surface import (
    get_vector_states as get_plot_vector_states,
)
from nxscli_pqg._plot_surface import (
    init_plot_data,
    init_surface_widget,
    numerical_channels,
)
from nxscli_pqg._plot_surface import (
    set_vector_visible as set_plot_vector_visible,
)
from nxscli_pqg._pqg_manager import PqgManager

if TYPE_CHECKING:
    from nxscli.trigger import TriggerHandler
    from nxslib.dev import DeviceChannel
    from PyQt6.QtGui import QKeyEvent


__all__ = [
    "PqgManager",
    "PlotDataCommon",
    "PlotDataAxesPqg",
    "DEFAULT_COLORS",
    "LINE_STYLES",
    "MARKERS",
    "parse_format_string",
    "PluginAnimationCommonPqg",
    "PlotWindow",
    "PluginPlotPqg",
    "EPlotMode",
    "PlotVectorState",
    "create_plot_surface",
    "build_plot_surface",
]


def build_plot_surface(
    phandler: Any, kwargs: dict[str, Any]
) -> "PluginPlotPqg":
    """Build plot surface from plugin handler and runtime kwargs."""
    chanlist = phandler.chanlist_plugin(kwargs["channels"])
    trig = phandler.triggers_plugin(chanlist, kwargs["trig"])
    cb = phandler.cb_get()
    return create_plot_surface(
        chanlist=chanlist,
        trig=trig,
        cb=cb,
        dpi=kwargs["dpi"],
        fmt=kwargs["fmt"],
        mode=str(kwargs.get("plot_mode", "detached")),
        parent=kwargs.get("plot_parent"),
    )


###############################################################################
# Class: PluginAnimationCommonPqg
###############################################################################


class PluginAnimationCommonPqg:
    """A class implementing a common pyqtgraph animation plot logic."""

    def __init__(
        self,
        pdata: PlotDataAxesPqg,
        qdata: PluginQueueData,
        write: str,
        hold_after_trigger: bool = False,
        hold_post_samples: int = 0,
    ):
        """Initialize animation handler.

        :param pdata: axes handler
        :param qdata: stream queue handler
        :param write: write path (for export)
        """
        self._sample_count = 0
        self._plot_data = pdata
        self._queue_data = qdata
        self._timer: QTimer | None = None
        self._write = write
        self._running = False
        self._hold_after_trigger = hold_after_trigger
        self._hold_post_samples = hold_post_samples
        self._held_on_trigger = False
        self._hold_trigger_x: float | None = None
        self._hold_stop_x: float | None = None

        # TODO: video export support (for now just log the path)
        if write:  # pragma: no cover
            logger.info("write path specified: %s (not implemented)", write)

    def _xy_buffers(self) -> tuple[list[list[Any]], list[list[Any]]]:
        return init_xy_buffers(self._queue_data.vdim)

    def _fetch_data_blocks(
        self, xdata: list[list[Any]], ydata: list[list[Any]]
    ) -> tuple[list[Any], list[Any], float | None]:
        del xdata, ydata
        xbuf, ybuf, self._sample_count, trigger_x = fetch_animation_data(
            self._queue_data,
            count=self._sample_count,
            stop_on_trigger=(
                self._hold_after_trigger and self._hold_post_samples == 0
            ),
        )
        return xbuf, ybuf, trigger_x

    def _flush_chunks(
        self,
        x_chunks: list[Any],
        y_chunks: list[list[Any]],
        xdata: list[list[Any]],
        ydata: list[list[Any]],
    ) -> None:
        """Flush chunk buffers into output lists."""
        flush_chunks(
            vdim=self._queue_data.vdim,
            x_chunks=x_chunks,
            y_chunks=y_chunks,
            xdata=xdata,
            ydata=ydata,
        )

    def _fetch_data(self) -> tuple[list[Any], list[Any], float | None]:
        """Fetch data from queue (non-blocking)."""
        xdata, ydata = self._xy_buffers()
        return self._fetch_data_blocks(xdata, ydata)

    def _animation_update(
        self, xdata: list[Any], ydata: list[Any], trigger_x: float | None
    ) -> None:
        """Update animation - to be overridden by subclasses."""
        pass  # pragma: no cover

    def _on_timer(self) -> None:  # pragma: no cover
        """Timer callback for animation update."""
        if not self._running:
            return

        xdata, ydata, trigger_x = self._fetch_data()
        xdata, ydata, trigger_x = self._trim_frame_for_hold(
            xdata,
            ydata,
            trigger_x,
        )

        if not has_frame_data(xdata, ydata):
            return

        self._animation_update(xdata, ydata, trigger_x)
        self._hold_on_trigger(xdata, trigger_x)

    def _trim_frame_for_hold(
        self,
        xdata: list[Any],
        ydata: list[Any],
        trigger_x: float | None,
    ) -> tuple[list[Any], list[Any], float | None]:
        """Trim the final hold frame to the configured post-trigger length."""
        if not self._hold_after_trigger:
            return xdata, ydata, trigger_x

        if trigger_x is not None and self._hold_trigger_x is None:
            self._hold_trigger_x = trigger_x
            if self._hold_post_samples > 0:
                self._hold_stop_x = (
                    trigger_x + float(self._hold_post_samples) - 0.5
                )

        if self._hold_stop_x is None:
            return xdata, ydata, trigger_x
        if not xdata or len(xdata[0]) == 0:
            return xdata, ydata, trigger_x

        keep = xdata[0] <= self._hold_stop_x
        if bool(keep.all()):
            return xdata, ydata, trigger_x

        trimmed_x = [series[keep] for series in xdata]
        trimmed_y = [series[keep] for series in ydata]
        return trimmed_x, trimmed_y, trigger_x

    def _hold_ready(self, latest_x: float | None) -> bool:
        """Return whether hold conditions are satisfied for the frame."""
        if self._hold_trigger_x is None:
            return False
        if self._hold_post_samples <= 0:
            return True
        if latest_x is None:
            return False
        assert self._hold_stop_x is not None
        return latest_x >= self._hold_stop_x

    def _hold_on_trigger(
        self, xdata: list[Any], trigger_x: float | None
    ) -> None:
        """Stop the timer after the first rendered trigger event."""
        if not self._hold_after_trigger or self._held_on_trigger:
            return
        if trigger_x is not None and self._hold_trigger_x is None:
            self._hold_trigger_x = trigger_x
            if self._hold_post_samples > 0:
                self._hold_stop_x = (
                    trigger_x + float(self._hold_post_samples) - 0.5
                )
        latest_x = None
        if xdata and len(xdata[0]) > 0:
            latest_x = float(xdata[0][-1])
        if not self._hold_ready(latest_x):
            return
        self._held_on_trigger = True
        PqgManager.process_events()
        self.stop()

    def start(self) -> None:
        """Start animation timer."""
        self._running = True
        self._timer = start_timer(
            self._on_timer, interval_ms=LIVE_TIMER_INTERVAL_MS
        )

    def stop(self) -> None:  # pragma: no cover
        """Stop animation."""
        self._running = False
        stop_timer(self._timer)
        self._timer = None

    def pause(self) -> None:  # pragma: no cover
        """Pause animation."""
        self._running = False

    def yscale_extend(
        self,
        ydata: list[list[Any]],
        plot_data: PlotDataAxesPqg,
        scale: float = 1.1,
    ) -> None:  # pragma: no cover
        """Extend yscale if needed with a given scale factor.

        :param ydata: Y data
        :param plot_data: axes handler
        :param scale: scale factor
        """
        del plot_data, scale
        # Let pyqtgraph auto-scale Y axis for now
        # This can be implemented if manual scaling is needed
        pass

    def xscale_extend(
        self,
        xdata: list[list[Any]],
        plot_data: PlotDataAxesPqg,
        scale: float = 2.0,
    ) -> None:  # pragma: no cover
        """Extend x axis if needed with a given scale factor.

        :param xdata: X data
        :param plot_data: axes handler
        :param scale: scale factor
        """
        del plot_data, scale
        # Let pyqtgraph auto-scale X axis for now
        # This can be implemented if manual scaling is needed
        pass


###############################################################################
# Class: PlotWindow
###############################################################################


class PlotWindow(QMainWindow):
    """Custom QMainWindow with keyboard shortcuts.

    Shortcuts:
    - 'q', 'Q', Escape: close window
    - 'f', 'F': toggle fullscreen
    """

    def keyPressEvent(  # pragma: no cover  # noqa: N802
        self, event: "QKeyEvent | None"
    ) -> None:
        """Handle key press events.

        Press 'q', 'Q', or Escape to close the window.
        Press 'f' or 'F' to toggle fullscreen.

        :param event: key event
        """
        if event is None:
            return
        key = event.key()
        if key in (Qt.Key.Key_Q, Qt.Key.Key_Escape):
            self.close()
        elif key == Qt.Key.Key_F:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()
        else:
            super().keyPressEvent(event)


###############################################################################
# Class: PluginPlotPqg
###############################################################################


class PluginPlotPqg(PluginData):
    """A class implementing pyqtgraph common plot handler."""

    def __init__(
        self,
        chanlist: list["DeviceChannel"],
        trig: list["TriggerHandler"],
        cb: PluginDataCb,
        dpi: float = DEFAULT_DPI,
        fmt: list[str] | None = None,
        mode: str = "detached",
        parent: QWidget | None = None,
    ):
        """Initialize a plot handler.

        :param chanlist: a list with plugin channels
        :param cb: plugin callback to nxslib
        :param dpi: figure DPI (used for window sizing)
        :param fmt: plot format
        """
        logger.info("prepare plot %s", str(chanlist))
        newchanlist = numerical_channels(chanlist)
        assert len(newchanlist) == len(trig)

        super().__init__(newchanlist, trig, cb)

        # Ensure QApplication exists
        PqgManager.get_app()

        self._mode = EPlotMode.from_text(mode)
        self._window, self._widget, layout = init_surface_widget(
            mode=self._mode,
            dpi=dpi,
            parent=parent,
            window_factory=PlotWindow,
        )

        self._plot_widgets: list[pg.PlotWidget] = []
        self._ani: list[PluginAnimationCommonPqg] = []

        self._fmt = expand_formats(self._chanlist, fmt)
        self._plot_widgets = build_plot_widgets(newchanlist, layout)
        self._plist = init_plot_data(
            self._chanlist,
            self._plot_widgets,
            self._fmt,
            PlotDataAxesPqg,
        )

        # Register window and show only for detached mode
        if self._window is not None:
            PqgManager.register_window(self._window)
            self._window.show()

    def __del__(self) -> None:  # pragma: no cover
        """Close window and clean queue handlers."""
        try:
            self.close()
        except RuntimeError:
            # Qt object already deleted
            pass
        super().__del__()

    @property
    def window(self) -> QMainWindow | None:
        """Get window handler."""
        return self._window

    @property
    def widget(self) -> QWidget:
        """Get embeddable widget."""
        return self._widget

    @property
    def mode(self) -> str:
        """Get plot mode string."""
        return self._mode.value

    @property
    def ani(self) -> list[PluginAnimationCommonPqg]:
        """Return all registered animation instances."""
        return self._ani

    @property
    def plist(self) -> list[PlotDataAxesPqg]:
        """Get plotdata list."""
        return self._plist

    def ani_append(self, ani: PluginAnimationCommonPqg) -> None:
        """Add animation.

        :param ani: plugin animation handler
        """
        self._ani.append(ani)

    def ani_clear(self) -> None:  # pragma: no cover
        """Clear animations."""
        self._ani = clear_plot_animations(self._ani)

    def plot_clear(self) -> None:
        """Clear plot data."""
        clear_plot_data(self._plist)

    def close(self) -> None:
        """Close detached window or attached widget."""
        close_surface(self._window, self._widget, PqgManager.unregister_window)

    def get_vector_states(self) -> list["PlotVectorState"]:
        """Get current vector visibility state."""
        return get_plot_vector_states(self._plist, PlotVectorState)

    def set_vector_visible(
        self, channel: int, vector: int, visible: bool
    ) -> None:
        """Set vector visibility in real time."""
        set_plot_vector_visible(
            self._plist,
            channel=channel,
            vector=vector,
            visible=visible,
        )

    def savefig(self, path: str) -> None:  # pragma: no cover
        """Save figure to file.

        :param path: output file path
        """
        # Use pyqtgraph's export functionality
        from pyqtgraph.exporters import ImageExporter  # type: ignore

        for i, pw in enumerate(self._plot_widgets):
            exporter = ImageExporter(pw.plotItem)
            if len(self._plot_widgets) > 1:
                # Add channel index to filename
                base, ext = path.rsplit(".", 1)
                out_path = f"{base}_{i}.{ext}"
            else:
                out_path = path
            exporter.export(out_path)
