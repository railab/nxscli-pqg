"""Shared test helpers for nxscli-pqg tests."""

from typing import Any


def make_plot_kwargs(**overrides: Any) -> dict[str, Any]:
    """Return minimal plugin startup kwargs for plot tests."""
    kwargs: dict[str, Any] = {
        "channels": [1],
        "trig": [],
        "dpi": 100,
        "fmt": [""],
        "write": "",
    }
    kwargs.update(overrides)
    return kwargs


class DummyAni:
    """Small animation fake with start/stop counters."""

    def __init__(self) -> None:
        self.started = 0
        self.stopped = 0

    def start(self) -> None:
        self.started += 1

    def stop(self) -> None:
        self.stopped += 1


class StopTrackingAni:
    """Animation fake that tracks active state via start/stop."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        del args
        del kwargs
        self.started = 0

    def start(self) -> None:
        self.started += 1

    def stop(self) -> None:
        self.started -= 1


class FakePluginHandler:
    """Minimal plugin handler fake for animation startup tests."""

    pass


class RecordingPluginHandler:
    """Plugin handler fake that records callback wiring."""

    def __init__(self) -> None:
        self.cb = object()

    def chanlist_plugin(self, channels: list[int]) -> list[str]:
        return [f"chan-{channel}" for channel in channels]

    def triggers_plugin(
        self, chanlist: list[str], trig: list[str]
    ) -> list[tuple[str, list[str], list[str]]]:
        return [("trig", chanlist, trig)]

    def cb_get(self) -> object:
        return self.cb


class FakePlot:
    """Minimal plot object exposing GUI-visible pqg attributes."""

    def __init__(self, *, mode: str = "detached") -> None:
        self.window = None if mode == "attached" else object()
        self.widget = object()
        self.mode = mode
        self.ani: list[Any] = []
        self.plist = [object()]
        self.qdlist = [object()]

    def ani_clear(self) -> None:
        self.ani = []

    def ani_append(self, ani: Any) -> None:
        self.ani.append(ani)


class DummyStaticPlotData:
    """Simple static-plot pdata fake with optional XY validation state."""

    def __init__(self, *, ydata: list[list[float]] | None = None) -> None:
        self.xlim: tuple[int, int] | None = None
        self.ydata = ydata if ydata is not None else [[0.0], [1.0]]

    def set_xlim(self, xlim: tuple[int, int]) -> None:
        self.xlim = xlim


class DummyStaticPlot:
    """Simple static plot fake with pdata and qdata lists."""

    def __init__(self, *, pdata: Any | None = None) -> None:
        self.plist = [pdata if pdata is not None else DummyStaticPlotData()]
        self.qdlist = [object()]
