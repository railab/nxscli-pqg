"""Dedicated polar plot plugin."""

from typing import Any

import numpy as np
from nxscli.logger import logger
from nxscli.transforms.operators_window import polar_relation

from nxscli_pqg._plot_constants import (
    AXIS_MAX_ABS_LIMIT,
    AXIS_MIN_MAGNITUDE,
    AXIS_PADDING_FACTOR,
)
from nxscli_pqg.plugins._typed_static import PluginTypedStatic


class PluginPolar(PluginTypedStatic):
    """Render static polar view from two channels (theta vs radius)."""

    plot_type = "polar"

    def __init__(self) -> None:
        """Initialize polar plugin."""
        super().__init__()
        self._single_channel_mode = False

    def start(self, kwargs: Any) -> bool:  # pragma: no cover
        """Start and validate polar channel selection."""
        ok = super().start(kwargs)
        if not ok:
            return False
        first_vdim = len(self._plot.plist[0].ydata)
        self._single_channel_mode = first_vdim >= 2
        if not self._single_channel_mode and len(self._plot.plist) < 2:
            raise ValueError(
                "polar plot requires channel with >=2 vectors or two channels"
            )
        return True

    def _render_pdata(self, pdata: Any) -> None:  # pragma: no cover
        """Render one polar chart from first two selected channels."""
        if pdata is not self._plot.plist[0]:
            try:
                pdata.plot_widget.hide()
            except Exception:
                pass
            return

        series, nvec = self._series_pairs(pdata)

        for i in range(nvec):
            theta, radius = self._theta_radius(series, i)
            xcart = radius * np.cos(theta)
            ycart = radius * np.sin(theta)
            pdata.curves[i].setData(xcart.tolist(), ycart.tolist())
            pdata.curves[i].setVisible(True)
        for i in range(nvec, len(pdata.curves)):
            pdata.curves[i].setData([], [])
            pdata.curves[i].setVisible(False)

        plot_item = pdata.plot_widget.getPlotItem()
        plot_item.setLabel("bottom", "x")
        plot_item.setLabel("left", "y")
        plot_item.setTitle("Polar Plot")
        view = pdata.plot_widget.getViewBox()
        view.setAspectLocked(True, ratio=1.0)
        self._apply_limits(pdata, series, nvec)
        logger.info(
            "polar rendered using channels %d/%d",
            self._plot.plist[0].chan,
            (
                self._plot.plist[0].chan
                if self._single_channel_mode
                else self._plot.plist[1].chan
            ),
        )

    def _series_pairs(  # pragma: no cover
        self, pdata: Any
    ) -> tuple[dict[str, Any], int]:
        first = self._plot.plist[0]
        if self._single_channel_mode:
            series = {
                "theta": [[float(v) for v in first.ydata[0]]],
                "radius": [[float(v) for v in first.ydata[1]]],
            }
            nvec = min(
                len(series["theta"]), len(series["radius"]), len(pdata.curves)
            )
            return series, nvec

        second = self._plot.plist[1]
        series = {
            "x": [[float(v) for v in vec] for vec in first.ydata],
            "y": [[float(v) for v in vec] for vec in second.ydata],
        }
        nvec = min(len(series["x"]), len(series["y"]), len(pdata.curves))
        return series, nvec

    def _theta_radius(  # pragma: no cover
        self, series: dict[str, Any], idx: int
    ) -> tuple[np.ndarray, np.ndarray]:
        if self._single_channel_mode:
            return (
                np.asarray(series["theta"][idx], dtype=np.float64),
                np.asarray(series["radius"][idx], dtype=np.float64),
            )
        rel = polar_relation(
            series["x"][idx],
            series["y"][idx],
            window=max(
                len(series["x"][idx]),
                len(series["y"][idx]),
                2,
            ),
        )
        return rel.theta, rel.radius

    def _apply_limits(  # pragma: no cover
        self, pdata: Any, series: dict[str, Any], nvec: int
    ) -> None:
        if nvec <= 0:
            return
        _, radius0 = self._theta_radius(series, 0)
        if int(radius0.size) <= 0:
            return
        finite = np.asarray(radius0, dtype=np.float64)
        finite = finite[np.isfinite(finite)]
        if int(finite.size) <= 0:
            return
        rmax = float(np.max(finite))
        if not np.isfinite(rmax) or abs(rmax) > AXIS_MAX_ABS_LIMIT:
            return
        lim = max(AXIS_MIN_MAGNITUDE, rmax) * AXIS_PADDING_FACTOR
        pdata.plot_widget.setXRange(-lim, lim, padding=0.0)
        pdata.plot_widget.setYRange(-lim, lim, padding=0.0)
