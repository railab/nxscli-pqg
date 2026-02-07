"""Shared windowed-plot helpers for pqg plugins."""

from typing import TYPE_CHECKING, Any

from nxscli.iplugin import IPluginPlotDynamic
from nxslib.nxscope import DNxscopeStreamBlock

from nxscli_pqg._plot_constants import WINDOWED_QUEUE_DRAIN_LIMIT
from nxscli_pqg.plot_pqg import PluginPlotPqg, PqgManager, build_plot_surface

if TYPE_CHECKING:
    from nxscli.idata import PluginQueueData
    from PyQt6.QtCore import QTimer


class _PluginWindowedBase(IPluginPlotDynamic):
    """Common windowed-plot lifecycle for pqg plugins."""

    def __init__(self) -> None:
        super().__init__()
        self._plot: "PluginPlotPqg"

    def get_plot_handler(self) -> "PluginPlotPqg | None":
        """Return the pyqtgraph plot handler or None before start."""
        return getattr(self, "_plot", None)

    @property
    def stream(self) -> bool:
        return True

    def data_wait(self, timeout: float = 0.0) -> bool:
        del timeout
        return True

    def wait_for_plugin(self) -> bool:  # pragma: no cover
        done = True
        if PqgManager.fig_is_open():
            done = False
            PqgManager.process_events()
        return done

    def _build_plot(self, kwargs: dict[str, Any]) -> None:
        assert self._phandler
        self._plot = build_plot_surface(self._phandler, kwargs)

    def result(self) -> "PluginPlotPqg":  # pragma: no cover
        if self._plot.window is not None:
            PqgManager.show(block=False)
        return self._plot


class _PluginAnimationListWindowedBase(_PluginWindowedBase):
    """Windowed pqg plugins that manage plot.ani handlers."""

    def stop(self) -> None:  # pragma: no cover
        if hasattr(self, "_plot") and len(self._plot.ani) > 0:
            for ani in self._plot.ani:
                ani.stop()

    def clear(self) -> None:  # pragma: no cover
        if hasattr(self, "_plot"):
            self._plot.ani_clear()


class _PluginTimerWindowedBase(_PluginWindowedBase):
    """Windowed pqg plugins driven by a Qt timer."""

    def __init__(self) -> None:
        super().__init__()
        self._timer: "QTimer | None" = None

    def stop(self) -> None:  # pragma: no cover
        if self._timer is not None:
            self._timer.stop()
            self._timer = None


def _read_channel_values(qdata: "PluginQueueData") -> list[float]:
    """Drain one-vector stream payloads into a flat float list."""
    vals: list[float] = []
    for _ in range(WINDOWED_QUEUE_DRAIN_LIMIT):
        payload = qdata.queue_get(block=False)
        if not payload:
            break
        if not isinstance(payload, list):
            continue
        for block in payload:
            if not isinstance(block, DNxscopeStreamBlock):
                continue
            arr = block.data
            if int(arr.shape[0]) == 0:
                continue
            vals.extend(float(x) for x in arr[:, 0].tolist())
    return vals


def _read_channel_pair(
    qdata: "PluginQueueData",
) -> tuple[list[float], list[float]]:
    """Drain two-vector stream payloads into paired float lists."""
    xs: list[float] = []
    ys: list[float] = []
    for _ in range(WINDOWED_QUEUE_DRAIN_LIMIT):
        payload = qdata.queue_get(block=False)
        if not payload:
            break
        if not isinstance(payload, list):
            continue
        for block in payload:
            if not isinstance(block, DNxscopeStreamBlock):
                continue
            arr = block.data
            if int(arr.shape[0]) == 0 or int(arr.shape[1]) < 2:
                continue
            xs.extend(float(x) for x in arr[:, 0].tolist())
            ys.extend(float(y) for y in arr[:, 1].tolist())
    return xs, ys


class _SingleChannelAccumulator:
    """Maintain a sliding single-channel paired buffer with hop gating."""

    def __init__(self, window: int, hop: int) -> None:
        self._window = window
        self._hop = hop
        self.reset()

    def reset(self) -> None:
        self.left: list[float] = []
        self.right: list[float] = []
        self.count = 0
        self.last_emit = 0

    def collect(
        self, xs: list[float], ys: list[float]
    ) -> tuple[list[float], list[float]] | None:
        count = min(len(xs), len(ys))
        if count > 0:
            self.left.extend(xs[:count])
            self.right.extend(ys[:count])
            self.count += count
            if len(self.left) > self._window:
                self.left = self.left[-self._window :]
                self.right = self.right[-self._window :]
        if self.count <= 0:
            return None
        if self.last_emit > 0 and self.count - self.last_emit < self._hop:
            return None
        self.last_emit = self.count
        return self.left, self.right
