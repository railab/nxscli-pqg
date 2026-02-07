"""Module containing the common pyqtgraph animation plugin logic."""

from abc import abstractmethod
from typing import TYPE_CHECKING, Any

from nxscli.iplugin import IPluginPlotDynamic
from nxscli.logger import logger

from nxscli_pqg.plot_pqg import (
    PlotDataAxesPqg,
    PluginAnimationCommonPqg,
    PluginPlotPqg,
    PqgManager,
    build_plot_surface,
)

if TYPE_CHECKING:
    from nxscli.idata import PluginQueueData


###############################################################################
# Function: _create_qt_inputhook
###############################################################################


def _create_qt_inputhook() -> Any:
    """Create an inputhook for Qt event processing.

    :return: inputhook function
    """
    try:
        from nxscli_pqg.plot_pqg import PqgManager

        def inputhook(inputhook_context: Any) -> None:
            """Process Qt events while waiting for input."""
            if PqgManager.fig_is_open():  # pragma: no cover
                PqgManager.process_events()

        return inputhook
    except ImportError:  # pragma: no cover
        return None


###############################################################################
# Class: IPluginAnimation
###############################################################################


class IPluginAnimation(IPluginPlotDynamic):
    """The common logic for an animation plugin."""

    def __init__(self) -> None:
        """Initialize an animation plugin."""
        super().__init__()

        self._plot: "PluginPlotPqg"

    @classmethod
    def get_inputhook(cls) -> Any:
        """Get Qt inputhook for GUI event processing.

        :return: inputhook function or None
        """
        return _create_qt_inputhook()

    def get_plot_handler(self) -> "PluginPlotPqg | None":
        """Return the pyqtgraph plot handler.

        :return: PluginPlotPqg instance, or None if start() has not been called
        """
        return getattr(self, "_plot", None)

    @abstractmethod
    def _start(
        self,
        pdata: "PlotDataAxesPqg",
        qdata: "PluginQueueData",
        kwargs: Any,
    ) -> "PluginAnimationCommonPqg":
        """Abstract method.

        :param pdata: axes handler
        :param qdata: stream queue handler
        :param kwargs: implementation specific arguments
        """

    @property
    def stream(self) -> bool:
        """Return True if this plugin needs stream."""
        return True

    def wait_for_plugin(self) -> bool:  # pragma: no cover
        """Wait for window to close."""
        done = True
        if PqgManager.fig_is_open():
            done = False
            # process events
            PqgManager.process_events()
        return done

    def stop(self) -> None:
        """Stop all animations."""
        assert self._plot

        if len(self._plot.ani) > 0:
            for ani in self._plot.ani:
                ani.stop()

    def clear(self) -> None:
        """Clear all animations."""
        assert self._plot

        self._plot.ani_clear()

    def data_wait(self, timeout: float = 0.0) -> bool:
        """Return True if data are ready.

        :param timeout: data wait timeout
        """
        return True

    def start(self, kwargs: Any) -> bool:
        """Start animation plugin.

        :param kwargs: implementation specific arguments
        """
        assert self._phandler

        logger.info("start %s", str(kwargs))

        self._plot = build_plot_surface(self._phandler, kwargs)

        # clear previous animations
        self.clear()

        # new animations
        for i, pdata in enumerate(self._plot.plist):
            ani = self._start(pdata, self._plot.qdlist[i], kwargs)
            self._plot.ani_append(ani)

        for ani in self._plot.ani:
            ani.start()

        return True

    def result(self) -> "PluginPlotPqg":
        """Get animation plugin result."""
        assert self._plot
        if self._plot.window is not None:
            PqgManager.show(block=False)
        return self._plot
