"""Tests for capture plugin."""

import numpy as np
from nxscli.trigger import DTriggerEvent
from nxslib.dev import DeviceChannel
from nxslib.nxscope import DNxscopeStreamBlock

from nxscli_pqg.plot_pqg import PlotDataCommon
from nxscli_pqg.plugins.snap import PluginSnap
from tests.helpers import (
    DummyStaticPlot,
    DummyStaticPlotData,
    make_plot_kwargs,
)


def test_plugincapture_init() -> None:
    """Test PluginSnap initialization."""
    plugin = PluginSnap()

    assert plugin.stream is True
    assert plugin.get_plot_handler() is None


def test_plugincapture_result_attached_mode() -> None:
    class DummyPlotData:
        def __init__(self) -> None:
            self.plotted = False
            self.trigger_x = None
            self.ydata = [[]]
            self.xdata = [[]]

        def xdata_extend(self, data) -> None:  # noqa: ANN001
            self.xdata = data

        def set_trigger_marker(self, xpos) -> None:  # noqa: ANN001
            self.trigger_x = xpos

        def set_xlim(self, xlim) -> None:  # noqa: ANN001
            self.xlim = xlim

        def plot(self) -> None:
            self.plotted = True

    class DummyPlot:
        def __init__(self) -> None:
            self.window = None
            self.plist = [DummyPlotData()]

    plugin = PluginSnap()
    plot = DummyPlot()
    plugin._plot = plot
    plugin._write = ""

    assert plugin.get_plot_handler() is plot

    ret = plugin.result()
    assert ret is plot
    assert plot.plist[0].plotted is True
    plot.plist[0].xdata_extend([[0]])
    plot.plist[0].set_trigger_marker(0.0)
    plot.plist[0].set_xlim((0, 0))
    assert plot.plist[0].xdata == [[0]]
    assert plot.plist[0].trigger_x == 0.0
    assert plot.plist[0].xlim == (0, 0)


def test_plugincapture_result_detached_shows_window_and_finalizes(
    mocker,
) -> None:
    class DummyPlotData:
        def __init__(self) -> None:
            self.plotted = False
            self.trigger_x = None
            self.ydata = [[]]
            self.xdata = [[]]

        def xdata_extend(self, data) -> None:  # noqa: ANN001
            self.xdata = data

        def set_trigger_marker(self, xpos) -> None:  # noqa: ANN001
            self.trigger_x = xpos

        def set_xlim(self, xlim) -> None:  # noqa: ANN001
            self.xlim = xlim

        def plot(self) -> None:
            self.plotted = True

    class DummyPlot:
        def __init__(self) -> None:
            self.window = object()
            self.plist = [DummyPlotData()]

    plugin = PluginSnap()
    plugin._plot = DummyPlot()
    plugin._write = ""
    show = mocker.patch("nxscli_pqg.plugins.snap.PqgManager.show")
    info = mocker.patch("nxscli_pqg.plugins.snap.logger.info")

    out = plugin.result()
    plugin._final()

    assert out is plugin._plot
    assert plugin._plot.plist[0].plotted is True
    plugin._plot.plist[0].xdata_extend([[0]])
    plugin._plot.plist[0].set_trigger_marker(0.0)
    plugin._plot.plist[0].set_xlim((0, 0))
    show.assert_called_once_with(block=False)
    info.assert_called_once_with("plot capture DONE")


def test_plugincapture_start_uses_build_plot_surface(mocker) -> None:
    """start() should reuse the common plot factory and x-axis setup."""

    plugin = PluginSnap()
    plugin.connect_phandler(object())
    plot = DummyStaticPlot(pdata=DummyStaticPlotData(ydata=[]))
    build = mocker.patch(
        "nxscli_pqg.plugins._static_common.build_plot_surface",
        return_value=plot,
    )
    thread_start = mocker.patch.object(plugin, "thread_start")

    out = plugin.start(
        make_plot_kwargs(samples=8, write="snap.png", nostop=True)
    )

    assert out is True
    build.assert_called_once_with(plugin._phandler, mocker.ANY)
    thread_start.assert_called_once_with(plot)
    assert plugin._write == "snap.png"
    assert plot.plist[0].xlim == (0, 8)


def test_plugincapture_start_with_zero_samples_keeps_default_xlim(
    mocker,
) -> None:
    """Zero samples should skip the initial x-limit update without failing."""

    plugin = PluginSnap()
    plugin.connect_phandler(object())
    plot = DummyStaticPlot(pdata=DummyStaticPlotData(ydata=[]))
    build = mocker.patch(
        "nxscli_pqg.plugins._static_common.build_plot_surface",
        return_value=plot,
    )
    thread_start = mocker.patch.object(plugin, "thread_start")

    out = plugin.start(make_plot_kwargs(samples=0, nostop=False))

    assert out is True
    build.assert_called_once_with(plugin._phandler, mocker.ANY)
    thread_start.assert_called_once_with(plot)
    assert plot.plist[0].xlim is None


def test_plugincapture_start_returns_false_for_empty_plot(mocker) -> None:
    """start() should fail cleanly when the plot factory returns no data."""

    class EmptyPlot:
        plist: list[object] = []
        qdlist: list[object] = []

    plugin = PluginSnap()
    plugin.connect_phandler(object())
    build = mocker.patch(
        "nxscli_pqg.plugins._static_common.build_plot_surface",
        return_value=EmptyPlot(),
    )
    thread_start = mocker.patch.object(plugin, "thread_start")

    out = plugin.start(make_plot_kwargs(samples=0, nostop=False))

    assert out is False
    build.assert_called_once_with(plugin._phandler, mocker.ANY)
    thread_start.assert_not_called()


def test_plugincapture_handle_blocks_updates_datalen() -> None:
    class Block:
        def __init__(self, data):  # noqa: ANN001
            self.data = data

    chan = DeviceChannel(chan=0, _type=2, vdim=2, name="chan0")

    class DummyPlot:
        def __init__(self) -> None:
            self.plist = [PlotDataCommon(chan)]

    plugin = PluginSnap()
    plugin._plot = DummyPlot()
    plugin._datalen = [0]
    pdata = type(
        "Q", (), {"vdim": 2, "pop_trigger_event": lambda self: None}
    )()
    plugin._handle_blocks(
        [Block(np.array([[1.0, 2.0], [3.0, 4.0]]))], pdata, 0
    )
    assert plugin._plot.plist[0].ydata == [[1.0, 3.0], [2.0, 4.0]]
    assert plugin._datalen[0] == 2


def test_plugincapture_handle_blocks_sets_trigger_marker() -> None:
    chan = DeviceChannel(chan=0, _type=2, vdim=1, name="chan0")

    class DummyPlot:
        def __init__(self) -> None:
            self.plist = [PlotDataCommon(chan)]

    class DummyQData:
        vdim = 1

        def pop_trigger_event(self):
            return DTriggerEvent(
                sample_index=1, channel=0, capture_mode="start_after"
            )

    plugin = PluginSnap()
    plugin._plot = DummyPlot()
    plugin._datalen = [2]
    plugin._handle_blocks(
        [DNxscopeStreamBlock(data=np.array([[5.0], [6.0]]), meta=None)],
        DummyQData(),
        0,
    )

    assert plugin._plot.plist[0].trigger_x == 3


def test_plugincapture_result_saves_when_write_set(mocker) -> None:
    """result() should forward saves through the shared static base."""

    class DummyPlotData:
        def __init__(self) -> None:
            self.trigger_x = None
            self.ydata = [[]]
            self.xdata = [[]]

        def xdata_extend(self, data) -> None:  # noqa: ANN001
            self.xdata = data

        def set_trigger_marker(self, xpos) -> None:  # noqa: ANN001
            self.trigger_x = xpos

        def set_xlim(self, xlim) -> None:  # noqa: ANN001
            self.xlim = xlim

        def plot(self) -> None:
            return

    class DummyPlot:
        def __init__(self) -> None:
            self.window = None
            self.plist = [DummyPlotData()]
            self.savefig = mocker.Mock()

    plugin = PluginSnap()
    plugin._plot = DummyPlot()
    plugin._write = "snap.png"

    out = plugin.result()

    assert out is plugin._plot
    plugin._plot.plist[0].xdata_extend([[0]])
    plugin._plot.plist[0].set_trigger_marker(0.0)
    plugin._plot.plist[0].set_xlim((0, 0))
    plugin._plot.savefig.assert_called_once_with("snap.png")


def test_plugincapture_result_rebases_trigger_to_zero() -> None:
    class DummyPlotData:
        def __init__(self) -> None:
            self.trigger_x = 3
            self.ydata = [[10.0, 11.0, 12.0, 13.0, 14.0]]
            self.xdata = [[]]
            self.xlim = None
            self.plotted = False

        def xdata_extend(self, data) -> None:  # noqa: ANN001
            self.xdata[0].extend(data[0])

        def set_trigger_marker(self, xpos) -> None:  # noqa: ANN001
            self.trigger_x = xpos

        def set_xlim(self, xlim) -> None:  # noqa: ANN001
            self.xlim = xlim

        def plot(self) -> None:
            self.plotted = True

    class DummyPlot:
        def __init__(self) -> None:
            self.window = None
            self.plist = [DummyPlotData()]

    plugin = PluginSnap()
    plugin._plot = DummyPlot()
    plugin._write = ""

    out = plugin.result()

    assert out is plugin._plot
    assert plugin._plot.plist[0].trigger_x == 0.0
    assert plugin._plot.plist[0].xdata[0] == [-3, -2, -1, 0, 1]
