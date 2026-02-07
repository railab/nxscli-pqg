"""Dedicated XY plot plugin."""

from typing import Any

from nxscli.logger import logger
from nxscli.transforms.operators_window import xy_relation

from nxscli_pqg.plugins._typed_static import PluginTypedStatic


class PluginXy(PluginTypedStatic):
    """Render static XY view (X channel vs Y channel)."""

    plot_type = "xy"

    def __init__(self) -> None:
        """Initialize XY plugin."""
        super().__init__()
        self._single_channel_mode = False

    def start(self, kwargs: Any) -> bool:  # pragma: no cover
        """Start and validate XY channel selection."""
        ok = super().start(kwargs)
        if not ok:
            return False
        first_vdim = len(self._plot.plist[0].ydata)
        self._single_channel_mode = first_vdim >= 2
        if not self._single_channel_mode and len(self._plot.plist) < 2:
            raise ValueError(
                "xy plot requires channel with >=2 vectors or two channels"
            )
        return True

    def _render_pdata(self, pdata: Any) -> None:  # pragma: no cover
        """Render one XY chart from first two selected channels."""
        if pdata is not self._plot.plist[0]:
            try:
                pdata.plot_widget.hide()
            except Exception:
                pass
            return

        first = self._plot.plist[0]
        if self._single_channel_mode:
            xsrc = [[float(v) for v in first.ydata[0]]]
            ysrc = [[float(v) for v in first.ydata[1]]]
        else:
            second = self._plot.plist[1]
            xsrc = [[float(v) for v in vec] for vec in first.ydata]
            ysrc = [[float(v) for v in vec] for vec in second.ydata]
        nvec = min(len(xsrc), len(ysrc), len(pdata.curves))

        for i in range(nvec):
            rel = xy_relation(
                xsrc[i], ysrc[i], window=max(len(xsrc[i]), len(ysrc[i]), 2)
            )
            pdata.curves[i].setData(rel.x.tolist(), rel.y.tolist())
            pdata.curves[i].setVisible(True)
        for i in range(nvec, len(pdata.curves)):
            pdata.curves[i].setData([], [])
            pdata.curves[i].setVisible(False)

        plot_item = pdata.plot_widget.getPlotItem()
        plot_item.setLabel("bottom", str(self._plot.plist[0].chan))
        plot_item.setLabel(
            "left",
            (
                str(self._plot.plist[0].chan)
                if self._single_channel_mode
                else str(self._plot.plist[1].chan)
            ),
        )
        plot_item.setTitle("XY Plot")
        logger.info(
            "xy rendered using channels %d vs %d",
            self._plot.plist[0].chan,
            (
                self._plot.plist[0].chan
                if self._single_channel_mode
                else self._plot.plist[1].chan
            ),
        )
