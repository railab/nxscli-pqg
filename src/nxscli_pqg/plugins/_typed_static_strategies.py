"""Private static render strategies for dedicated plot types."""

from typing import Protocol, Sequence, cast

import numpy as np
import pyqtgraph as pg  # type: ignore
from nxscli.transforms.operators_window import (
    fft_spectrum,
    histogram_counts,
    xy_relation,
)


class _CurveLike(Protocol):
    """Minimal pyqtgraph curve surface used by static strategies."""

    def setVisible(self, visible: bool) -> None:  # noqa: N802
        """Set curve visibility."""
        raise NotImplementedError


class _PlotItemLike(Protocol):
    """Minimal plot item surface used by histogram rendering."""

    def addItem(self, item: object) -> None:  # noqa: N802
        """Add a graphics item to the plot."""
        raise NotImplementedError

    def removeItem(self, item: object) -> None:  # noqa: N802
        """Remove a graphics item from the plot."""
        raise NotImplementedError


class _PlotWidgetLike(Protocol):
    """Minimal plot widget surface used by static strategies."""

    def getPlotItem(self) -> _PlotItemLike:  # noqa: N802
        """Return the underlying plot item."""
        raise NotImplementedError


class _StaticPlotDataLike(Protocol):
    """Minimal plot-data surface used by static strategies."""

    @property
    def plot_widget(self) -> _PlotWidgetLike:
        """Return the plot widget."""
        raise NotImplementedError

    @property
    def curves(self) -> Sequence[_CurveLike]:
        """Return renderable curves."""
        raise NotImplementedError


class _HistogramItemsPlotDataLike(_StaticPlotDataLike, Protocol):
    """Static plot data with histogram item storage."""

    _hist_items: list[object]


class StaticRenderStrategy(Protocol):
    """Behavior contract for one static plot rendering mode."""

    def build_xy(  # pragma: no cover
        self,
        series: list[list[float]],
        *,
        samples: int,
        hist_bins: int,
    ) -> tuple[list[list[float]], list[list[float]]]:
        """Build x/y values for line-based rendering."""
        raise NotImplementedError

    def render(  # pragma: no cover
        self,
        pdata: _StaticPlotDataLike,
        series: list[list[float]],
        *,
        samples: int,
        hist_bins: int,
    ) -> bool:
        """Render directly and return whether default rendering is skipped."""
        raise NotImplementedError


class TimeseriesStaticStrategy:
    """Default line rendering for raw sample series."""

    def build_xy(  # pragma: no cover
        self,
        series: list[list[float]],
        *,
        samples: int,
        hist_bins: int,
    ) -> tuple[list[list[float]], list[list[float]]]:
        """Build x/y pairs for raw timeseries lines."""
        del samples, hist_bins
        xvals = [[float(i) for i in range(len(vec))] for vec in series]
        return xvals, series

    def render(  # pragma: no cover
        self,
        pdata: _StaticPlotDataLike,
        series: list[list[float]],
        *,
        samples: int,
        hist_bins: int,
    ) -> bool:
        """Leave rendering to the default line path."""
        del pdata, series, samples, hist_bins
        return False


class FftStaticStrategy:
    """Line rendering strategy for FFT plots."""

    def build_xy(  # pragma: no cover
        self,
        series: list[list[float]],
        *,
        samples: int,
        hist_bins: int,
    ) -> tuple[list[list[float]], list[list[float]]]:
        """Build FFT frequency/amplitude series."""
        del samples, hist_bins
        xvals: list[list[float]] = []
        yvals: list[list[float]] = []
        for vec in series:
            res = fft_spectrum(vec, window_fn="hann")
            if int(res.freq.size) == 0:
                xvals.append([])
                yvals.append([])
                continue
            xvals.append([float(x) for x in res.freq.tolist()])
            yvals.append([float(y) for y in res.amplitude.tolist()])
        return xvals, yvals

    def render(  # pragma: no cover
        self,
        pdata: _StaticPlotDataLike,
        series: list[list[float]],
        *,
        samples: int,
        hist_bins: int,
    ) -> bool:
        """Leave rendering to the default line path."""
        del pdata, series, samples, hist_bins
        return False


class HistogramStaticStrategy:
    """Bar rendering strategy for histogram plots."""

    def build_xy(
        self,
        series: list[list[float]],
        *,
        samples: int,
        hist_bins: int,
    ) -> tuple[list[list[float]], list[list[float]]]:
        """Build histogram edge/count series."""
        del samples
        bins = max(1, hist_bins)
        xvals: list[list[float]] = []
        yvals: list[list[float]] = []
        for vec in series:
            res = histogram_counts(vec, bins=bins, range_mode="auto")
            if int(res.counts.size) == 0 or int(res.edges.size) < 2:
                xvals.append([])
                yvals.append([])
                continue
            xvals.append([float(x) for x in res.edges[:-1].tolist()])
            yvals.append([float(y) for y in res.counts.tolist()])
        return xvals, yvals

    def render(
        self,
        pdata: _StaticPlotDataLike,
        series: list[list[float]],
        *,
        samples: int,
        hist_bins: int,
    ) -> bool:
        """Render histogram bars directly on the plot widget."""
        del samples
        bins = max(1, hist_bins)
        plot_item = pdata.plot_widget.getPlotItem()
        old_items = getattr(pdata, "_hist_items", [])
        for item in old_items:
            try:
                plot_item.removeItem(item)
            except Exception:
                pass

        hist_items = []
        for i, vec in enumerate(series):
            res = histogram_counts(vec, bins=bins, range_mode="auto")
            if int(res.counts.size) == 0 or int(res.edges.size) < 2:
                continue
            centers = res.edges[:-1]
            widths = np.diff(res.edges)
            brush = (50 + (i * 70) % 200, 120, 220, 140 if i == 0 else 90)
            bars = pg.BarGraphItem(
                x=centers,
                height=res.counts,
                width=widths,
                brush=brush,
            )
            plot_item.addItem(bars)
            hist_items.append(bars)

        hist_pdata = cast("_HistogramItemsPlotDataLike", pdata)
        hist_pdata._hist_items = hist_items
        for curve in pdata.curves:
            curve.setVisible(False)
        return True


class XyStaticStrategy:
    """Scatter strategy for XY relation plots."""

    _fallback = TimeseriesStaticStrategy()

    def build_xy(
        self,
        series: list[list[float]],
        *,
        samples: int,
        hist_bins: int,
    ) -> tuple[list[list[float]], list[list[float]]]:
        """Build XY relation coordinates for paired series."""
        del hist_bins
        if len(series) < 2:
            return self._fallback.build_xy(
                series, samples=samples, hist_bins=0
            )
        xvals: list[list[float]] = []
        yvals: list[list[float]] = []
        for i in range(1, len(series)):
            rel = xy_relation(series[0], series[i], window=samples or 65536)
            xvals.append([float(x) for x in rel.x.tolist()])
            yvals.append([float(y) for y in rel.y.tolist()])
        return xvals, yvals

    def render(
        self,
        pdata: _StaticPlotDataLike,
        series: list[list[float]],
        *,
        samples: int,
        hist_bins: int,
    ) -> bool:
        """Leave rendering to the default line path."""
        del pdata, series, samples, hist_bins
        return False


_TIMESERIES = TimeseriesStaticStrategy()
_STRATEGIES: dict[str, StaticRenderStrategy] = {
    "timeseries": _TIMESERIES,
    "fft": FftStaticStrategy(),
    "histogram": HistogramStaticStrategy(),
    "xy": XyStaticStrategy(),
}


def get_static_strategy(plot_type: str) -> StaticRenderStrategy:
    """Return the dedicated strategy for a plot type."""
    return _STRATEGIES.get(plot_type, _TIMESERIES)
