"""Shared windowed dynamic plugins for typed plots."""

from typing import TYPE_CHECKING, Any, cast

import numpy as np
from nxscli.logger import logger
from nxscli.transforms.models import PolarResult, XyResult
from nxscli.transforms.operators_window import (
    polar_relation,
    xy_relation,
)
from nxscli.transforms.pipeline import (
    TransformPipeline,
    WindowBinaryProcessor,
    WindowUnaryProcessor,
)
from PyQt6.QtCore import QTimer

from nxscli_pqg._plot_constants import (
    AXIS_DECAY_FACTOR,
    AXIS_MIN_MAGNITUDE,
    AXIS_PADDING_FACTOR,
    RELATION_TIMER_INTERVAL_MS,
    XY_PADDING_RATIO,
)
from nxscli_pqg.animation_pqg import _create_qt_inputhook
from nxscli_pqg.plot_pqg import PluginAnimationCommonPqg
from nxscli_pqg.plugins._typed_windowed_strategies import (
    WindowedTransformState,
    _finite_min_max,
    _safe_range,
    get_windowed_transform_strategy,
)
from nxscli_pqg.plugins._windowed_common import (
    _PluginAnimationListWindowedBase,
    _PluginTimerWindowedBase,
    _read_channel_pair,
    _read_channel_values,
    _SingleChannelAccumulator,
)

if TYPE_CHECKING:
    from nxscli.idata import PluginQueueData

    from nxscli_pqg.plot_pqg import PlotDataAxesPqg


class _WindowedTypedAnimation(PluginAnimationCommonPqg):
    """Windowed transform animation for FFT/histogram."""

    def __init__(
        self,
        pdata: "PlotDataAxesPqg",
        qdata: "PluginQueueData",
        write: str,
        *,
        plot_type: str,
        window: int,
        hop: int,
        bins: int,
        window_fn: str,
        range_mode: str,
    ) -> None:
        super().__init__(pdata, qdata, write)
        self._plot_type = plot_type
        self._window = max(2, int(window))
        self._hop = int(hop)
        self._bins = max(1, int(bins))
        self._window_fn = str(window_fn)
        self._range_mode = str(range_mode)
        self._strategy = get_windowed_transform_strategy(plot_type)
        self._strategy_state = WindowedTransformState()
        self._pipeline = TransformPipeline(max_points=self._window)
        self._proc_names: list[str] = []
        for i, _ in enumerate(pdata.curves):
            name = f"curve{i}"
            self._proc_names.append(name)
            self._pipeline.register(
                WindowUnaryProcessor(
                    name=name,
                    channel=name,
                    window=self._window,
                    hop=self._hop,
                    fn=self._processor_fn,
                )
            )
        pdata.samples_max = self._window

    def _animation_update(  # pragma: no cover
        self,
        xdata: list[Any],
        ydata: list[Any],
        trigger_x: float | None = None,
    ) -> None:
        del trigger_x
        plot_data = self._plot_data
        plot_data.xdata_extend_max(xdata)
        plot_data.ydata_extend_max(ydata)
        batch = {
            name: [float(x) for x in vec]
            for name, vec in zip(self._proc_names, ydata)
        }
        outputs = self._pipeline.ingest(batch)
        self._strategy.update_plot(
            plot_data,
            outputs,
            proc_names=self._proc_names,
            state=self._strategy_state,
        )

    def _processor_fn(self, window: np.ndarray) -> object:  # pragma: no cover
        return self._strategy.processor(
            window,
            bins=self._bins,
            window_fn=self._window_fn,
            range_mode=self._range_mode,
            state=self._strategy_state,
        )


class _PluginTypedWindowed(_PluginAnimationListWindowedBase):
    """Windowed dynamic plugin for one typed transform."""

    plot_type = "fft"

    def __init__(self) -> None:
        super().__init__()

    @classmethod
    def get_inputhook(cls) -> Any:  # pragma: no cover
        return _create_qt_inputhook()

    def start(self, kwargs: Any) -> bool:  # pragma: no cover
        logger.info("start %s stream %s", self.plot_type, str(kwargs))
        self._build_plot(kwargs)
        self.clear()
        for i, pdata in enumerate(self._plot.plist):
            ani = _WindowedTypedAnimation(
                pdata,
                self._plot.qdlist[i],
                kwargs["write"],
                plot_type=self.plot_type,
                window=int(kwargs["window"]),
                hop=int(kwargs.get("hop", 0)),
                bins=int(kwargs.get("bins", 32)),
                window_fn=str(kwargs.get("window_fn", "hann")),
                range_mode=str(kwargs.get("range_mode", "auto")),
            )
            self._plot.ani_append(ani)
            ani.start()
        return True


class _RelationWindowedBase(_PluginTimerWindowedBase):
    """Common relation-stream setup and collection for windowed plots."""

    relation_name = ""
    missing_channel_message = ""

    def __init__(self) -> None:
        super().__init__()
        self._window = 256
        self._hop = 64
        self._align_policy = "truncate"
        self._pipeline: TransformPipeline
        self._single_channel_mode = False
        self._single = _SingleChannelAccumulator(window=256, hop=64)

    @classmethod
    def get_inputhook(cls) -> Any:  # pragma: no cover
        return _create_qt_inputhook()

    def _transform_relation(  # pragma: no cover
        self, left: list[float], right: list[float]
    ) -> object:
        raise NotImplementedError

    def _transform_pipeline_relation(
        self, left: list[float], right: list[float]
    ) -> object:  # pragma: no cover
        return self._transform_relation(left, right)

    def _extract_relation_result(  # pragma: no cover
        self, raw: object
    ) -> object | None:
        raise NotImplementedError

    def _setup_relation_stream(self, kwargs: Any) -> None:  # pragma: no cover
        assert self._phandler
        chanlist = self._phandler.chanlist_plugin(kwargs["channels"])
        if len(chanlist) < 1:
            raise ValueError(self.missing_channel_message)
        self._build_plot(kwargs)
        self._window = max(2, int(kwargs["window"]))
        self._hop = max(1, int(kwargs.get("hop", 0) or (self._window // 4)))
        self._align_policy = str(kwargs.get("align_policy", "truncate"))
        first_vdim = self._plot.qdlist[0].vdim
        self._single_channel_mode = first_vdim >= 2
        if not self._single_channel_mode and len(self._plot.qdlist) < 2:
            raise ValueError(self.missing_channel_message)
        self._pipeline = TransformPipeline(max_points=self._window)
        self._pipeline.register(
            WindowBinaryProcessor(
                name=self.relation_name,
                left_channel="x",
                right_channel="y",
                window=self._window,
                hop=self._hop,
                fn=lambda x, y: self._transform_pipeline_relation(
                    x.tolist(),
                    y.tolist(),
                ),
            )
        )
        self._single = _SingleChannelAccumulator(
            window=self._window, hop=self._hop
        )
        self._hide_secondary_plots()

    def _hide_secondary_plots(self) -> None:  # pragma: no cover
        for idx, pdata in enumerate(self._plot.plist):
            if idx != 0:
                pdata.plot_widget.hide()

    def _collect_relation(self) -> object | None:  # pragma: no cover
        if self._single_channel_mode:
            xs, ys = _read_channel_pair(self._plot.qdlist[0])
            collected = self._single.collect(xs, ys)
            if collected is None:
                return None
            left, right = collected
            return self._transform_relation(left, right)

        xs = _read_channel_values(self._plot.qdlist[0])
        ys = _read_channel_values(self._plot.qdlist[1])
        count = min(len(xs), len(ys))
        outputs = self._pipeline.ingest({"x": xs[:count], "y": ys[:count]})
        return self._extract_relation_result(outputs.get(self.relation_name))


class _PluginXyWindowed(_RelationWindowedBase):
    """Windowed XY scatter animation using two channels."""

    relation_name = "xy"
    missing_channel_message = (
        "xy_stream requires channel with >=2 vectors or two channels"
    )

    def __init__(self) -> None:
        super().__init__()
        self._xlim: tuple[float, float] | None = None
        self._ylim: tuple[float, float] | None = None

    def start(self, kwargs: Any) -> bool:  # pragma: no cover
        self._setup_relation_stream(kwargs)
        self._xlim = None
        self._ylim = None
        self._timer = QTimer()
        self._timer.timeout.connect(self._update_xy)
        self._timer.start(RELATION_TIMER_INTERVAL_MS)
        return True

    def _transform_relation(  # pragma: no cover
        self, left: list[float], right: list[float]
    ) -> XyResult:
        return xy_relation(
            left,
            right,
            window=self._window,
            align_policy=self._align_policy,
        )

    def _extract_relation_result(  # pragma: no cover
        self, raw: object
    ) -> XyResult | None:
        if raw is None or not isinstance(raw, XyResult):
            return None
        return raw

    def _update_xy(self) -> None:  # pragma: no cover
        relation = self._collect_relation()
        if relation is None:
            return
        rel = cast("XyResult", relation)

        pdata = self._plot.plist[0]
        if len(pdata.curves) == 0:
            return
        pdata.curves[0].setData(rel.x.tolist(), rel.y.tolist())
        pdata.curves[0].setVisible(True)
        for i in range(1, len(pdata.curves)):
            pdata.curves[i].setVisible(False)
        pdata.plot_widget.setTitle("XY Stream")
        x_mm = _finite_min_max(rel.x)
        y_mm = _finite_min_max(rel.y)
        if x_mm is not None and y_mm is not None:
            xmin, xmax = x_mm
            ymin, ymax = y_mm
            padx = max(AXIS_MIN_MAGNITUDE, (xmax - xmin) * XY_PADDING_RATIO)
            pady = max(AXIS_MIN_MAGNITUDE, (ymax - ymin) * XY_PADDING_RATIO)
            cur_xlim = (xmin - padx, xmax + padx)
            cur_ylim = (ymin - pady, ymax + pady)
            if self._xlim is None:
                self._xlim = cur_xlim
                self._ylim = cur_ylim
            else:
                assert self._ylim is not None
                self._xlim = (
                    min(self._xlim[0], cur_xlim[0]),
                    max(self._xlim[1], cur_xlim[1]),
                )
                self._ylim = (
                    min(self._ylim[0], cur_ylim[0]),
                    max(self._ylim[1], cur_ylim[1]),
                )
            xr = _safe_range(self._xlim[0], self._xlim[1])
            yr = _safe_range(self._ylim[0], self._ylim[1])
            if xr is not None:
                pdata.plot_widget.setXRange(*xr, padding=0.0)
            if yr is not None:
                pdata.plot_widget.setYRange(*yr, padding=0.0)


class PluginFftStream(_PluginTypedWindowed):
    """FFT stream plot."""

    plot_type = "fft"


class PluginHistStream(_PluginTypedWindowed):
    """Histogram stream plot."""

    plot_type = "histogram"


class PluginXyStream(_PluginXyWindowed):
    """XY stream plot."""


class _PluginPolarWindowed(_RelationWindowedBase):
    """Windowed polar animation using two channels."""

    relation_name = "polar"
    missing_channel_message = (
        "polar_stream requires channel with >=2 vectors or two channels"
    )

    def __init__(self) -> None:
        super().__init__()
        self._rmax: float | None = None

    def start(self, kwargs: Any) -> bool:  # pragma: no cover
        self._setup_relation_stream(kwargs)
        self._rmax = None
        self._timer = QTimer()
        self._timer.timeout.connect(self._update_polar)
        self._timer.start(RELATION_TIMER_INTERVAL_MS)
        return True

    def _update_polar(self) -> None:  # pragma: no cover
        relation = self._collect_relation()
        if relation is None:
            return
        theta, radius = cast("tuple[np.ndarray, np.ndarray]", relation)

        pdata = self._plot.plist[0]
        if len(pdata.curves) == 0:
            return
        xcart = radius * np.cos(theta)
        ycart = radius * np.sin(theta)
        pdata.curves[0].setData(xcart.tolist(), ycart.tolist())
        pdata.curves[0].setVisible(True)
        for i in range(1, len(pdata.curves)):
            pdata.curves[i].setData([], [])
            pdata.curves[i].setVisible(False)
        pdata.plot_widget.setTitle("Polar Stream")
        pdata.plot_widget.getViewBox().setAspectLocked(True, ratio=1.0)
        mm = _finite_min_max(radius)
        if mm is not None:
            cur = mm[1]
            if self._rmax is None:
                self._rmax = cur
            else:
                self._rmax = max(cur, self._rmax * AXIS_DECAY_FACTOR)
            lim = max(AXIS_MIN_MAGNITUDE, self._rmax) * AXIS_PADDING_FACTOR
            sr = _safe_range(-lim, lim)
            if sr is not None:
                pdata.plot_widget.setXRange(*sr, padding=0.0)
                pdata.plot_widget.setYRange(*sr, padding=0.0)

    def _transform_relation(  # pragma: no cover
        self, left: list[float], right: list[float]
    ) -> tuple[np.ndarray, np.ndarray]:
        return (
            np.asarray(left, dtype=np.float64),
            np.asarray(right, dtype=np.float64),
        )

    def _transform_pipeline_relation(  # pragma: no cover
        self, left: list[float], right: list[float]
    ) -> PolarResult:
        return polar_relation(
            left,
            right,
            window=self._window,
            align_policy=self._align_policy,
        )

    def _extract_relation_result(  # pragma: no cover
        self, raw: object
    ) -> tuple[np.ndarray, np.ndarray] | None:
        if raw is None or not isinstance(raw, PolarResult):
            return None
        return raw.theta, raw.radius


class PluginPolarStream(_PluginPolarWindowed):
    """Polar stream plot."""
