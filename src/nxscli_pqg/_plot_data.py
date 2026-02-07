"""Private pyqtgraph plot-data helpers."""

from typing import TYPE_CHECKING, Any

import pyqtgraph as pg  # type: ignore

from nxscli_pqg._plot_format import (
    DEFAULT_COLORS,
    LINE_STYLES,
    MARKERS,
    parse_format_string,
)

if TYPE_CHECKING:
    from nxslib.dev import DeviceChannel


def _series_values(series: Any) -> list[Any] | Any:
    """Convert ndarray-like inputs to Python lists for list-backed storage."""
    if hasattr(series, "tolist"):
        return series.tolist()
    return series


class PlotDataCommon:
    """A class implementing common plot data."""

    def __init__(self, channel: "DeviceChannel"):
        """Initialize common plot data for one channel."""
        self._xdata: list[list[Any]] = []
        self._ydata: list[list[Any]] = []
        self._vdim = channel.data.vdim
        self._chan = channel.data.chan
        for _ in range(self._vdim):
            self._xdata.append([])
            self._ydata.append([])
        self._samples_max = 0
        self._trigger_x: float | None = None

    @property
    def chan(self) -> int:
        """Return the channel id."""
        return self._chan

    @property
    def xdata(self) -> list[list[Any]]:
        """Return X-axis data."""
        return self._xdata

    @property
    def ydata(self) -> list[list[Any]]:
        """Return Y-axis data."""
        return self._ydata

    @property
    def samples_max(self) -> int:
        """Return the maximum retained sample count."""
        return self._samples_max

    @samples_max.setter
    def samples_max(self, smax: int) -> None:
        """Set the maximum retained sample count."""
        self._samples_max = smax

    @property
    def trigger_x(self) -> float | None:
        """Return last trigger marker X position."""
        return self._trigger_x

    def set_trigger_marker(self, xpos: float | None) -> None:
        """Store trigger marker X position."""
        self._trigger_x = xpos

    def xdata_extend(self, data: list[list[Any]]) -> None:
        """Append X-axis data."""
        for i, xdata in enumerate(self._xdata):
            xdata.extend(_series_values(data[i]))

    def ydata_extend(self, data: list[list[Any]]) -> None:
        """Append Y-axis data."""
        for i, ydata in enumerate(self._ydata):
            ydata.extend(_series_values(data[i]))

    def xdata_extend_max(self, data: list[list[Any]]) -> None:
        """Append X-axis data and clamp to the sample limit."""
        for i, _ in enumerate(self._xdata):
            self._xdata[i].extend(_series_values(data[i]))
            remove = len(self._xdata[i]) - self._samples_max
            if remove > 0:
                self._xdata[i] = self._xdata[i][remove:]

    def ydata_extend_max(self, data: list[list[Any]]) -> None:
        """Append Y-axis data and clamp to the sample limit."""
        for i, _ in enumerate(self._xdata):
            self._ydata[i].extend(_series_values(data[i]))
            remove = len(self._ydata[i]) - self._samples_max
            if remove > 0:
                self._ydata[i] = self._ydata[i][remove:]


class PlotDataAxesPqg(PlotDataCommon):
    """A class implementing common pyqtgraph axes logic."""

    def __init__(
        self,
        plot_widget: pg.PlotWidget,
        channel: "DeviceChannel",
        fmt: list[str] | None = None,
    ):
        """Initialize pyqtgraph-specific plot data."""
        super().__init__(channel)

        if not channel.data.is_numerical:
            raise TypeError

        self._plot_widget = plot_widget
        self._plot_item = plot_widget.getPlotItem()
        if not fmt:
            self._fmt = [
                DEFAULT_COLORS[i % len(DEFAULT_COLORS)]
                for i in range(channel.data.vdim)
            ]
        else:
            assert (
                len(fmt) == channel.data.vdim
            ), "fmt must match vectors in configured channel"
            self._fmt = fmt

        self._curves: list[pg.PlotDataItem] = []
        for i in range(channel.data.vdim):
            fmt_parsed = parse_format_string(self._fmt[i])
            pen_kwargs: dict[str, Any] = {"width": 1}
            if fmt_parsed["color"]:
                pen_kwargs["color"] = fmt_parsed["color"]
            else:
                pen_kwargs["color"] = DEFAULT_COLORS[i % len(DEFAULT_COLORS)]
            if fmt_parsed["linestyle"]:
                pen_kwargs["style"] = LINE_STYLES[fmt_parsed["linestyle"]]
            pen = pg.mkPen(**pen_kwargs)

            plot_kwargs: dict[str, Any] = {"pen": pen}
            if fmt_parsed["marker"]:
                plot_kwargs["symbol"] = MARKERS[fmt_parsed["marker"]]
                plot_kwargs["symbolSize"] = 8
                plot_kwargs["symbolBrush"] = pen_kwargs.get("color", "w")

            curve = self._plot_widget.plot([], [], **plot_kwargs)
            self._curves.append(curve)
        self._trigger_line = pg.InfiniteLine(
            angle=90,
            movable=False,
            pen=pg.mkPen(color="#ff00ff", width=2),
        )
        self._trigger_line.setZValue(1000)
        self._trigger_line.hide()
        self._plot_item.addItem(self._trigger_line)

        self.grid_set(True)
        if len(channel.data.name) > 0:  # pragma: no cover
            self.plot_title = channel.data.name

    def __str__(self) -> str:
        """Return a compact debug representation."""
        return "PlotDataAxesPqg" + "(channel=" + str(self.chan) + ")"

    @property
    def plot_widget(self) -> pg.PlotWidget:
        """Return the plot widget."""
        return self._plot_widget

    @property
    def curves(self) -> list[pg.PlotDataItem]:
        """Return animated curve items."""
        return self._curves

    @property
    def trigger_line(self) -> pg.InfiniteLine:
        """Return trigger marker line."""
        return self._trigger_line

    @property
    def xlim(self) -> tuple[Any, Any]:  # pragma: no cover
        """Return current X limits."""
        assert self._plot_item
        view_range = self._plot_item.viewRange()
        return (view_range[0][0], view_range[0][1])

    @property
    def ylim(self) -> tuple[Any, Any]:  # pragma: no cover
        """Return current Y limits."""
        assert self._plot_item
        view_range = self._plot_item.viewRange()
        return (view_range[1][0], view_range[1][1])

    @property
    def plot_title(self) -> str:
        """Return the plot title."""
        assert self._plot_item
        return str(self._plot_item.titleLabel.text)

    @plot_title.setter
    def plot_title(self, title: str) -> None:
        """Set the plot title."""
        assert self._plot_item
        self._plot_item.setTitle(title)

    def set_xlim(self, xlim: tuple[Any, Any]) -> None:
        """Set X-axis limits."""
        assert self._plot_item
        self._plot_item.setXRange(xlim[0], xlim[1], padding=0)

    def set_ylim(self, ylim: tuple[Any, Any]) -> None:
        """Set Y-axis limits."""
        assert self._plot_item
        self._plot_item.setYRange(ylim[0], ylim[1], padding=0)

    def enable_auto_range(self, x: bool = True, y: bool = True) -> None:
        """Enable auto-ranging on selected axes."""
        assert self._plot_item
        self._plot_item.enableAutoRange(x=x, y=y)

    def disable_auto_range(self) -> None:
        """Disable auto-ranging."""
        assert self._plot_item
        self._plot_item.disableAutoRange()

    def plot(self) -> None:  # pragma: no cover
        """Plot all stored series."""
        for i, ydata in enumerate(self._ydata):
            if self._xdata[i]:
                self._curves[i].setData(self._xdata[i], ydata)
            else:
                self._curves[i].setData(ydata)
        if self._trigger_x is not None:
            self._trigger_line.setValue(self._trigger_x)
            self._trigger_line.show()

    def xaxis_disable(self) -> None:
        """Hide X-axis ticks."""
        assert self._plot_item
        self._plot_item.getAxis("bottom").setTicks([])

    def grid_set(self, enable: bool) -> None:
        """Enable or disable the grid."""
        assert self._plot_item
        self._plot_item.showGrid(x=enable, y=enable)
