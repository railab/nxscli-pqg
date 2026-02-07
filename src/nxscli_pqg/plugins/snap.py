"""Module containing capture plugin."""

from typing import TYPE_CHECKING, Any

from nxscli.logger import logger

from nxscli_pqg.plot_pqg import PqgManager
from nxscli_pqg.plugins._static_common import _PluginStaticBase

if TYPE_CHECKING:
    from nxscli_pqg.plot_pqg import PluginPlotPqg


###############################################################################
# Class: PluginSnap
###############################################################################


class PluginSnap(_PluginStaticBase):
    """Plugin that plots static captured data."""

    def __init__(self) -> None:
        """Initialize a capture plot plugin."""
        super().__init__()

    def _final(self) -> None:
        logger.info("plot capture DONE")

    def wait_for_plugin(self) -> bool:  # pragma: no cover
        """Wait for window to close."""
        done = True
        if PqgManager.fig_is_open():
            done = False
            # process events
            PqgManager.process_events()
        return done

    def start(self, kwargs: Any) -> bool:
        """Start capture plugin.

        :param kwargs: implementation specific arguments
        """
        logger.info("start capture %s", str(kwargs))
        if not self._start_plot(kwargs):
            return False

        self._set_initial_xlim()

        self.thread_start(self._plot)

        return True

    def result(self) -> "PluginPlotPqg":
        """Get capture plugin result."""
        assert self._plot

        # plot all data
        for pdata in self._plot.plist:
            if pdata.trigger_x is not None and pdata.ydata and pdata.ydata[0]:
                rel_x = [
                    idx - pdata.trigger_x for idx in range(len(pdata.ydata[0]))
                ]
                pdata.xdata_extend([rel_x[:] for _ in range(len(pdata.ydata))])
                pdata.set_trigger_marker(0.0)
                pdata.set_xlim((rel_x[0], rel_x[-1]))
            pdata.plot()

        self._save_plot()

        if self._plot.window is not None:
            PqgManager.show(block=False)
        return self._plot
