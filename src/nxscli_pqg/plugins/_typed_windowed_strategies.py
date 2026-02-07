"""Private windowed transform strategies for FFT and histogram plots."""

from dataclasses import dataclass
from typing import Protocol, Sequence, cast

import numpy as np
import pyqtgraph as pg  # type: ignore
from nxscli.transforms.models import FftResult, HistogramResult
from nxscli.transforms.operators_window import fft_spectrum, histogram_counts

from nxscli_pqg._plot_constants import (
    AXIS_DECAY_FACTOR,
    AXIS_MAX_ABS_LIMIT,
    AXIS_MIN_MAGNITUDE,
    AXIS_PADDING_FACTOR,
)


class _CurveLike(Protocol):
    """Minimal pyqtgraph curve surface used by windowed strategies."""

    def setData(self, x: object, y: object) -> None:  # noqa: N802
        """Assign curve data."""
        raise NotImplementedError

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
    """Minimal plot widget surface used by windowed strategies."""

    def setXRange(  # noqa: N802
        self, low: float, high: float, padding: float = 0.0
    ) -> None:
        """Set x range."""
        raise NotImplementedError

    def setYRange(  # noqa: N802
        self, low: float, high: float, padding: float = 0.0
    ) -> None:
        """Set y range."""
        raise NotImplementedError

    def getPlotItem(self) -> _PlotItemLike:  # noqa: N802
        """Return the underlying plot item."""
        raise NotImplementedError


class _WindowedPlotDataLike(Protocol):
    """Minimal plot-data surface used by windowed strategies."""

    @property
    def curves(self) -> Sequence[_CurveLike]:
        """Return renderable curves."""
        raise NotImplementedError

    @property
    def plot_widget(self) -> _PlotWidgetLike:
        """Return the plot widget."""
        raise NotImplementedError


class _HistogramItemsPlotDataLike(_WindowedPlotDataLike, Protocol):
    """Windowed plot data with histogram item storage."""

    _hist_items: list[object]


@dataclass
class WindowedTransformState:
    """Mutable state shared across windowed transform updates."""

    fft_xmax: float | None = None
    ymax_locked: float | None = None
    hist_range: tuple[float, float] | None = None


class WindowedTransformStrategy(Protocol):
    """Behavior contract for one windowed transform type."""

    def processor(
        self,
        window: np.ndarray,
        *,
        bins: int,
        window_fn: str,
        range_mode: str,
        state: WindowedTransformState,
    ) -> object:
        """Transform one window of samples."""
        raise NotImplementedError

    def update_plot(
        self,
        pdata: _WindowedPlotDataLike,
        outputs: dict[str, object],
        *,
        proc_names: list[str],
        state: WindowedTransformState,
    ) -> None:
        """Apply transform outputs to the plot state."""
        raise NotImplementedError


def _finite_min_max(  # pragma: no cover
    arr: np.ndarray,
) -> tuple[float, float] | None:
    vals = np.asarray(arr, dtype=np.float64)
    finite = vals[np.isfinite(vals)]
    if int(finite.size) == 0:
        return None
    low = float(np.min(finite))
    high = float(np.max(finite))
    if (
        abs(low) > AXIS_MAX_ABS_LIMIT
        or abs(high) > AXIS_MAX_ABS_LIMIT
        or low > high
    ):
        return None
    return low, high


def _safe_range(  # pragma: no cover
    low: float, high: float
) -> tuple[float, float] | None:
    if not np.isfinite(low) or not np.isfinite(high):
        return None
    if abs(low) > AXIS_MAX_ABS_LIMIT or abs(high) > AXIS_MAX_ABS_LIMIT:
        return None
    if low > high:
        return None
    if low == high:
        eps = max(AXIS_MIN_MAGNITUDE, abs(low) * 1e-6)
        return low - eps, high + eps
    return low, high


def _lock_axis(  # pragma: no cover
    pdata: _WindowedPlotDataLike,
    state: WindowedTransformState,
    *,
    xmax: float | None,
    ymax: float,
) -> None:
    if not np.isfinite(ymax):
        return
    ymax_safe = max(AXIS_MIN_MAGNITUDE, float(ymax))
    if state.ymax_locked is None:
        state.ymax_locked = ymax_safe
    else:
        prev = state.ymax_locked
        if ymax_safe > prev:
            state.ymax_locked = 0.85 * prev + 0.15 * ymax_safe
        else:
            state.ymax_locked = max(ymax_safe, prev * AXIS_DECAY_FACTOR)

    if xmax is not None:
        xr = _safe_range(0.0, float(xmax))
        if xr is not None:
            pdata.plot_widget.setXRange(*xr, padding=0.0)
    yr = _safe_range(0.0, float(state.ymax_locked) * AXIS_PADDING_FACTOR)
    if yr is not None:
        pdata.plot_widget.setYRange(*yr, padding=0.0)


class FftWindowedStrategy:
    """FFT-specific windowed transform behavior."""

    def processor(
        self,
        window: np.ndarray,
        *,
        bins: int,
        window_fn: str,
        range_mode: str,
        state: WindowedTransformState,
    ) -> object:
        """Compute FFT output for a single window."""
        del bins, range_mode, state
        return fft_spectrum(window, window_fn=window_fn)

    def update_plot(  # pragma: no cover
        self,
        pdata: _WindowedPlotDataLike,
        outputs: dict[str, object],
        *,
        proc_names: list[str],
        state: WindowedTransformState,
    ) -> None:
        """Apply FFT transform outputs to curves and axes."""
        ymax = 0.0
        for i, curve in enumerate(pdata.curves):
            raw = outputs.get(proc_names[i])
            if raw is None or not isinstance(raw, FftResult):
                continue
            curve.setData(raw.freq.tolist(), raw.amplitude.tolist())
            if int(raw.freq.size) > 0:
                state.fft_xmax = float(raw.freq[-1])
            mm = _finite_min_max(raw.amplitude)
            if mm is not None:
                ymax = max(ymax, mm[1])
        _lock_axis(pdata, state, xmax=state.fft_xmax, ymax=ymax)


class HistogramWindowedStrategy:
    """Histogram-specific windowed transform behavior."""

    def processor(
        self,
        window: np.ndarray,
        *,
        bins: int,
        window_fn: str,
        range_mode: str,
        state: WindowedTransformState,
    ) -> object:
        """Compute histogram output for a single window."""
        del window_fn
        mode, value_range = self._hist_mode(range_mode, state.hist_range)
        return histogram_counts(
            window,
            bins=bins,
            range_mode=mode,
            value_range=value_range,
        )

    def update_plot(  # pragma: no cover
        self,
        pdata: _WindowedPlotDataLike,
        outputs: dict[str, object],
        *,
        proc_names: list[str],
        state: WindowedTransformState,
    ) -> None:
        """Redraw histogram bars and update axis locks."""
        updates = self._collect_updates(outputs, proc_names)
        if not updates:
            return

        if state.hist_range is None:
            first_edges = updates[0][1]
            if int(first_edges.size) >= 2:
                state.hist_range = (
                    float(first_edges[0]),
                    float(first_edges[-1]),
                )

        plot_item = pdata.plot_widget.getPlotItem()
        self._clear_items(plot_item, getattr(pdata, "_hist_items", []))
        hist_items, ymax = self._draw_updates(plot_item, updates)

        hist_pdata = cast("_HistogramItemsPlotDataLike", pdata)
        hist_pdata._hist_items = hist_items
        for curve in pdata.curves:
            curve.setVisible(False)
        if state.hist_range is not None:
            pdata.plot_widget.setXRange(
                state.hist_range[0], state.hist_range[1], padding=0.0
            )
        _lock_axis(pdata, state, xmax=None, ymax=ymax)

    def _hist_mode(  # pragma: no cover
        self,
        range_mode: str,
        hist_range: tuple[float, float] | None,
    ) -> tuple[str, tuple[float, float] | None]:
        """Resolve histogram mode and optional fixed range."""
        if range_mode == "fixed":
            return "fixed", hist_range
        if hist_range is None:
            return "auto", None
        return "fixed", hist_range

    def _collect_updates(  # pragma: no cover
        self,
        outputs: dict[str, object],
        proc_names: list[str],
    ) -> list[tuple[np.ndarray, np.ndarray]]:
        """Collect histogram outputs that are ready to render."""
        updates: list[tuple[np.ndarray, np.ndarray]] = []
        for name in proc_names:
            raw = outputs.get(name)
            if raw is None or not isinstance(raw, HistogramResult):
                continue
            updates.append((raw.counts, raw.edges))
        return updates

    def _clear_items(  # pragma: no cover
        self, plot_item: _PlotItemLike, items: list[object]
    ) -> None:
        """Remove existing histogram graphics from the plot item."""
        for item in items:
            try:
                plot_item.removeItem(item)
            except Exception:
                pass

    def _draw_updates(  # pragma: no cover
        self,
        plot_item: _PlotItemLike,
        updates: list[tuple[np.ndarray, np.ndarray]],
    ) -> tuple[list[object], float]:
        """Draw histogram bars for all collected outputs."""
        hist_items: list[object] = []
        ymax = 0.0
        for i, (counts, edges) in enumerate(updates):
            if int(edges.size) < 2:
                continue
            centers = edges[:-1]
            widths = np.diff(edges)
            brush = (50 + (i * 70) % 200, 120, 220, 140 if i == 0 else 90)
            bars = pg.BarGraphItem(
                x=centers,
                height=counts,
                width=widths,
                brush=brush,
            )
            plot_item.addItem(bars)
            hist_items.append(bars)
            mm = _finite_min_max(counts)
            if mm is not None:
                ymax = max(ymax, mm[1])
        return hist_items, ymax


_FFT = FftWindowedStrategy()
_STRATEGIES: dict[str, WindowedTransformStrategy] = {
    "fft": _FFT,
    "histogram": HistogramWindowedStrategy(),
}


def get_windowed_transform_strategy(
    plot_type: str,
) -> WindowedTransformStrategy:
    """Return the dedicated strategy for a plot type."""
    return _STRATEGIES.get(plot_type, _FFT)
