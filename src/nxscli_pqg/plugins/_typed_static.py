"""Shared static-plot plugin base for dedicated plot-type plugins."""

from typing import TYPE_CHECKING, Any

from nxscli.logger import logger

from nxscli_pqg.plot_pqg import PqgManager
from nxscli_pqg.plugins._static_common import _PluginStaticBase
from nxscli_pqg.plugins._typed_static_strategies import get_static_strategy

if TYPE_CHECKING:
    from nxscli_pqg.plot_pqg import PluginPlotPqg


class PluginTypedStatic(_PluginStaticBase):
    """Static plot plugin for one explicit rendering type."""

    plot_type = "timeseries"

    def __init__(self) -> None:
        """Initialize typed static plugin."""
        super().__init__()
        self._hist_bins: int = 32

    def _final(self) -> None:
        logger.info("plot %s DONE", self.plot_type)

    def wait_for_plugin(self) -> bool:  # pragma: no cover
        """Wait for window to close."""
        done = True
        if PqgManager.fig_is_open():
            done = False
            PqgManager.process_events()
        return done

    def start(self, kwargs: Any) -> bool:  # pragma: no cover
        """Start typed static plugin."""
        logger.info("start %s %s", self.plot_type, str(kwargs))
        self._hist_bins = int(kwargs.get("bins", 32))
        if not self._start_plot(kwargs):
            return False

        if self._samples and self.plot_type in ("timeseries", "xy"):
            self._set_initial_xlim()

        self.thread_start(self._plot)
        return True

    def result(self) -> "PluginPlotPqg":  # pragma: no cover
        """Render and return plot."""
        assert self._plot

        for pdata in self._plot.plist:
            self._render_pdata(pdata)

        self._save_plot()

        if self._plot.window is not None:
            PqgManager.show(block=False)
        return self._plot

    def _render_pdata(self, pdata: Any) -> None:  # pragma: no cover
        series = [[float(v) for v in vec] for vec in pdata.ydata]
        strategy = get_static_strategy(self.plot_type)
        if strategy.render(
            pdata,
            series,
            samples=self._samples,
            hist_bins=self._hist_bins,
        ):
            return
        xvals, yvals = strategy.build_xy(
            series,
            samples=self._samples,
            hist_bins=self._hist_bins,
        )
        for i, curve in enumerate(pdata.curves):
            if i < len(yvals):
                curve.setData(xvals[i], yvals[i])
            else:
                curve.setData([], [])
        for curve in pdata.curves:
            curve.setVisible(True)
