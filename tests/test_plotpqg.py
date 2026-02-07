"""Tests for plot_pqg module."""

import queue

import numpy as np
import pytest
from nxscli.idata import PluginDataCb, PluginQueueData
from nxscli.trigger import (
    DTriggerConfig,
    DTriggerEvent,
    ETriggerType,
    TriggerHandler,
)
from nxslib.dev import DeviceChannel
from nxslib.nxscope import DNxscopeStreamBlock

from nxscli_pqg._animation_common import fetch_animation_data
from nxscli_pqg._animation_lifecycle import has_frame_data, stop_timer
from nxscli_pqg._plot_factory import (
    build_plot_surface as build_plot_surface_private,
)
from nxscli_pqg._plot_surface import build_plot_widgets
from nxscli_pqg.plot_pqg import (
    EPlotMode,
    PlotDataAxesPqg,
    PlotDataCommon,
    PluginAnimationCommonPqg,
    PluginPlotPqg,
    PqgManager,
    build_plot_surface,
    create_plot_surface,
    parse_format_string,
)
from tests.helpers import RecordingPluginHandler


def test_plotdatacommon() -> None:
    """Test PlotDataCommon class."""
    chan = DeviceChannel(0, 1, 2, "chan0")
    x = PlotDataCommon(chan)

    assert x.samples_max == 0
    x.samples_max = 100
    assert x.samples_max == 100

    assert x.xdata == [[], []]
    assert x.ydata == [[], []]

    x.xdata_extend([[1, 2], [3, 4]])
    x.ydata_extend([[5, 6], [7, 8]])
    assert x.xdata == [[1, 2], [3, 4]]
    assert x.ydata == [[5, 6], [7, 8]]
    x.xdata_extend([[9], [10]])
    x.ydata_extend([[11], [12]])
    assert x.xdata == [[1, 2, 9], [3, 4, 10]]
    assert x.ydata == [[5, 6, 11], [7, 8, 12]]

    x.samples_max = 5
    x.xdata_extend_max([[13, 14], [16, 17]])
    x.ydata_extend_max([[19, 20], [22, 23]])
    x.xdata_extend_max([[15], [18]])
    x.ydata_extend_max([[21], [24]])

    assert x.xdata == [[2, 9, 13, 14, 15], [4, 10, 16, 17, 18]]
    assert x.ydata == [[6, 11, 19, 20, 21], [8, 12, 22, 23, 24]]
    x.xdata_extend_max([[25], [26]])
    x.ydata_extend_max([[27], [28]])
    assert x.xdata == [[9, 13, 14, 15, 25], [10, 16, 17, 18, 26]]
    assert x.ydata == [[11, 19, 20, 21, 27], [12, 22, 23, 24, 28]]

    y = PlotDataCommon(chan)
    y.xdata_extend([np.array([29, 30]), np.array([31, 32])])
    y.ydata_extend([np.array([33, 34]), np.array([35, 36])])
    assert y.xdata == [[29, 30], [31, 32]]
    assert y.ydata == [[33, 34], [35, 36]]


def test_pqgmanager_configure() -> None:
    """Test PqgManager configuration."""
    PqgManager.configure(background="k", foreground="w", antialias=True)
    PqgManager.configure(background="w", foreground="k", antialias=False)


def test_plotdataaxespqg() -> None:
    """Test PlotDataAxesPqg class."""
    import pyqtgraph as pg

    # Ensure QApplication exists
    PqgManager.get_app()

    plot_widget = pg.PlotWidget()

    # not numerical channels
    chan = DeviceChannel(0, 1, 2, "chan0")
    with pytest.raises(TypeError):
        PlotDataAxesPqg(plot_widget, chan)

    chan = DeviceChannel(chan=0, _type=2, vdim=2, name="chan0")
    x = PlotDataAxesPqg(plot_widget, chan)

    assert x.plot_widget is plot_widget
    assert str(x) is not None
    assert len(x.curves) == 2

    x.set_xlim((0, 1))
    x.set_ylim((2, 3))

    x.plot_title = "test"
    assert x.plot_title == "test"

    x.plot()
    assert x.trigger_line.isVisible() is False
    x.set_trigger_marker(2.5)
    x.plot()
    assert x.trigger_line.isVisible() is True
    x.xaxis_disable()
    x.grid_set(True)
    x.grid_set(False)
    x.enable_auto_range(x=True, y=True)
    x.disable_auto_range()

    x = PlotDataAxesPqg(plot_widget, chan, fmt=None)
    assert len(x._fmt) == 2

    x = PlotDataAxesPqg(plot_widget, chan, fmt=["r", "b"])
    assert x._fmt == ["r", "b"]

    plot_widget.close()


def test_build_plot_widgets_ignores_non_numerical_channels() -> None:
    """Surface helper should only create widgets for numerical channels."""
    import pyqtgraph as pg
    from PyQt6.QtWidgets import QVBoxLayout, QWidget

    PqgManager.get_app()
    host = QWidget()
    layout = QVBoxLayout(host)
    chanlist = [
        DeviceChannel(chan=0, _type=1, vdim=1, name="meta"),
        DeviceChannel(chan=1, _type=2, vdim=1, name="num"),
    ]

    widgets = build_plot_widgets(chanlist, layout)

    assert len(widgets) == 1
    assert isinstance(widgets[0], pg.PlotWidget)
    widgets[0].close()
    host.close()


def test_pluginanimationcommonpqg() -> None:
    """Test PluginAnimationCommonPqg class."""
    import pyqtgraph as pg

    PqgManager.get_app()

    q: queue.Queue = queue.Queue()
    chan = DeviceChannel(chan=0, _type=2, vdim=2, name="chan0")
    plot_widget = pg.PlotWidget()
    pdata = PlotDataAxesPqg(plot_widget, chan)
    dtc = DTriggerConfig(ETriggerType.ALWAYS_OFF)
    trig = TriggerHandler(0, dtc)
    qdata = PluginQueueData(q, chan, trig)
    x = PluginAnimationCommonPqg(pdata, qdata, "")

    x.start()
    x.pause()
    x.stop()

    trig.cleanup()
    plot_widget.close()


def test_pluginanimationcommonpqg_trim_for_hold_passthrough() -> None:
    """Hold trimming should leave frames unchanged when not active."""
    import pyqtgraph as pg

    PqgManager.get_app()

    q: queue.Queue = queue.Queue()
    chan = DeviceChannel(chan=0, _type=2, vdim=1, name="chan0")
    plot_widget = pg.PlotWidget()
    pdata = PlotDataAxesPqg(plot_widget, chan)
    dtc = DTriggerConfig(ETriggerType.ALWAYS_OFF)
    trig = TriggerHandler(0, dtc)
    qdata = PluginQueueData(q, chan, trig)
    ani = PluginAnimationCommonPqg(
        pdata,
        qdata,
        "",
        hold_after_trigger=False,
    )
    xdata = [np.array([1.0, 2.0])]
    ydata = [np.array([3.0, 4.0])]

    trimmed = ani._trim_frame_for_hold(xdata, ydata, None)

    assert trimmed == (xdata, ydata, None)

    trig.cleanup()
    plot_widget.close()


def test_pqg_animation_has_frame_data() -> None:
    """Lifecycle helper should detect empty and non-empty frames."""
    assert has_frame_data([[1.0]], [[2.0]]) is True
    assert has_frame_data([[]], [[2.0]]) is False
    assert has_frame_data([[1.0]], [[]]) is False
    assert has_frame_data([np.array([1.0])], [np.array([2.0])]) is True
    assert has_frame_data([np.array([])], [np.array([2.0])]) is False
    stop_timer(None)


def test_fetch_animation_data_returns_numpy_arrays() -> None:
    """Queue drain should keep fetched frame data ndarray-backed."""

    class FakeQueueData:
        vdim = 2

        def __init__(self) -> None:
            self._payloads = [
                [
                    DNxscopeStreamBlock(
                        data=np.array([[1.0, 2.0], [3.0, 4.0]]),
                        meta=np.array([[0], [1]]),
                    )
                ],
                [],
            ]
            self._event = DTriggerEvent(
                sample_index=1,
                channel=3,
                capture_mode="start_after",
            )

        def queue_get(self, block: bool = False):  # noqa: ANN001, ARG002
            return self._payloads.pop(0)

        def pop_trigger_event(self) -> DTriggerEvent | None:
            event = self._event
            self._event = None
            return event

    qdata = FakeQueueData()

    xdata, ydata, next_count, trigger_x = fetch_animation_data(qdata, count=0)

    assert next_count == 2
    assert trigger_x == 1
    assert all(isinstance(series, np.ndarray) for series in xdata)
    assert all(isinstance(series, np.ndarray) for series in ydata)
    assert np.array_equal(xdata[0], np.array([0, 1]))
    assert np.array_equal(xdata[1], np.array([0, 1]))
    assert np.array_equal(ydata[0], np.array([1.0, 3.0]))
    assert np.array_equal(ydata[1], np.array([2.0, 4.0]))


def test_pluginanimationcommonpqg_flush_chunks_handles_empty_inputs() -> None:
    """Chunk flushing should tolerate missing x and y payloads."""
    import pyqtgraph as pg

    PqgManager.get_app()

    q: queue.Queue = queue.Queue()
    chan = DeviceChannel(chan=0, _type=2, vdim=2, name="chan0")
    plot_widget = pg.PlotWidget()
    pdata = PlotDataAxesPqg(plot_widget, chan)
    dtc = DTriggerConfig(ETriggerType.ALWAYS_OFF)
    trig = TriggerHandler(0, dtc)
    qdata = PluginQueueData(q, chan, trig)
    ani = PluginAnimationCommonPqg(pdata, qdata, "")
    xdata = [[], []]
    ydata = [[], []]

    ani._flush_chunks([], [[], []], xdata, ydata)
    ani._flush_chunks(
        [np.array([1, 2])], [[], [np.array([3.0, 4.0])]], xdata, ydata
    )

    assert xdata == [[1, 2], [1, 2]]
    assert ydata == [[], [3.0, 4.0]]

    trig.cleanup()
    plot_widget.close()


def test_pluginanimationcommonpqg_trim_handles_empty_xdata() -> None:
    """Hold trimming should tolerate empty x buffers."""
    import pyqtgraph as pg

    PqgManager.get_app()

    q: queue.Queue = queue.Queue()
    chan = DeviceChannel(chan=0, _type=2, vdim=1, name="chan0")
    plot_widget = pg.PlotWidget()
    pdata = PlotDataAxesPqg(plot_widget, chan)
    dtc = DTriggerConfig(ETriggerType.ALWAYS_OFF)
    trig = TriggerHandler(0, dtc)
    qdata = PluginQueueData(q, chan, trig)
    ani = PluginAnimationCommonPqg(
        pdata,
        qdata,
        "",
        hold_after_trigger=True,
        hold_post_samples=2,
    )
    ani._hold_trigger_x = 4.0
    ani._hold_stop_x = 5.5

    trimmed = ani._trim_frame_for_hold([np.array([])], [np.array([])], None)

    assert len(trimmed[0]) == 1
    assert len(trimmed[1]) == 1
    assert np.array_equal(trimmed[0][0], np.array([]))
    assert np.array_equal(trimmed[1][0], np.array([]))
    assert trimmed[2] is None

    trig.cleanup()
    plot_widget.close()


def test_pluginanimationcommonpqg_hold_on_trigger_reuses_existing_state(
    mocker,
) -> None:
    """Hold stop threshold should not be recomputed after first trigger."""
    import pyqtgraph as pg

    PqgManager.get_app()

    q: queue.Queue = queue.Queue()
    chan = DeviceChannel(chan=0, _type=2, vdim=1, name="chan0")
    plot_widget = pg.PlotWidget()
    pdata = PlotDataAxesPqg(plot_widget, chan)
    dtc = DTriggerConfig(ETriggerType.ALWAYS_OFF)
    trig = TriggerHandler(0, dtc)
    qdata = PluginQueueData(q, chan, trig)
    ani = PluginAnimationCommonPqg(
        pdata,
        qdata,
        "",
        hold_after_trigger=True,
        hold_post_samples=3,
    )
    stop = mocker.patch.object(ani, "stop")
    process_events = mocker.patch(
        "nxscli_pqg.plot_pqg.PqgManager.process_events"
    )
    ani._hold_trigger_x = 4.0
    ani._hold_stop_x = 6.5

    ani._hold_on_trigger([np.array([4.0, 5.0, 6.0, 7.0])], 5.0)

    assert ani._hold_stop_x == 6.5
    stop.assert_called_once_with()
    process_events.assert_called_once_with()

    trig.cleanup()
    plot_widget.close()


def test_pluginanimationcommonpqg_hold_on_trigger_sets_stop_x(
    mocker,
) -> None:
    """First trigger should initialize hold state without stopping early."""
    import pyqtgraph as pg

    PqgManager.get_app()

    q: queue.Queue = queue.Queue()
    chan = DeviceChannel(chan=0, _type=2, vdim=1, name="chan0")
    plot_widget = pg.PlotWidget()
    pdata = PlotDataAxesPqg(plot_widget, chan)
    dtc = DTriggerConfig(ETriggerType.ALWAYS_OFF)
    trig = TriggerHandler(0, dtc)
    qdata = PluginQueueData(q, chan, trig)
    ani = PluginAnimationCommonPqg(
        pdata,
        qdata,
        "",
        hold_after_trigger=True,
        hold_post_samples=3,
    )
    stop = mocker.patch.object(ani, "stop")
    process_events = mocker.patch(
        "nxscli_pqg.plot_pqg.PqgManager.process_events"
    )

    ani._hold_on_trigger([np.array([4.0, 5.0])], 4.0)

    assert ani._hold_trigger_x == 4.0
    assert ani._hold_stop_x == 6.5
    stop.assert_not_called()
    process_events.assert_not_called()

    trig.cleanup()
    plot_widget.close()


def test_pluginanimationcommonpqg_hold_on_trigger_without_post_samples(
    mocker,
) -> None:
    """Immediate hold should still latch trigger X without stop threshold."""
    import pyqtgraph as pg

    PqgManager.get_app()

    q: queue.Queue = queue.Queue()
    chan = DeviceChannel(chan=0, _type=2, vdim=1, name="chan0")
    plot_widget = pg.PlotWidget()
    pdata = PlotDataAxesPqg(plot_widget, chan)
    dtc = DTriggerConfig(ETriggerType.ALWAYS_OFF)
    trig = TriggerHandler(0, dtc)
    qdata = PluginQueueData(q, chan, trig)
    ani = PluginAnimationCommonPqg(
        pdata,
        qdata,
        "",
        hold_after_trigger=True,
        hold_post_samples=0,
    )
    stop = mocker.patch.object(ani, "stop")
    process_events = mocker.patch(
        "nxscli_pqg.plot_pqg.PqgManager.process_events"
    )

    ani._hold_on_trigger([np.array([4.0])], 4.0)

    assert ani._hold_trigger_x == 4.0
    assert ani._hold_stop_x is None
    stop.assert_called_once_with()
    process_events.assert_called_once_with()

    trig.cleanup()
    plot_widget.close()


def dummy_stream_sub(ch: int) -> queue.Queue:
    """Dummy stream subscribe callback."""
    return queue.Queue()


def dummy_stream_unsub(q: queue.Queue) -> None:
    """Dummy stream unsubscribe callback."""
    pass


def make_plot(
    chanlist: list[DeviceChannel],
    *,
    mode: str = "detached",
    fmt=None,
) -> PluginPlotPqg:
    """Create a test plot with default callback and triggers."""
    dtc = DTriggerConfig(ETriggerType.ALWAYS_OFF)
    trig = [
        TriggerHandler(chan.data.chan, dtc)
        for chan in chanlist
        if chan.data.is_numerical
    ]
    cb = PluginDataCb(dummy_stream_sub, dummy_stream_unsub)
    return PluginPlotPqg(chanlist, trig, cb, mode=mode, fmt=fmt)


def test_pluginplotpqg() -> None:
    """Test PluginPlotPqg class."""
    chanlist = [
        DeviceChannel(chan=0, _type=1, vdim=2, name="chan0"),  # not numerical
        DeviceChannel(chan=1, _type=2, vdim=1, name="chan1"),
        DeviceChannel(chan=2, _type=2, vdim=2, name="chan2"),
    ]
    x = make_plot(chanlist)

    assert x.window is not None
    assert x.ani == []
    assert len(x.plist) > 0
    assert len(x._chanlist) == 2  # one channel not numerical
    assert x._fmt == [None, None]

    x.plot_clear()
    x.window.close()
    del x

    # test fmt configuration
    x = make_plot(chanlist, fmt="r")
    assert x._fmt == [["r"], ["r", "r"]]
    x.window.close()
    del x

    x = make_plot(chanlist, fmt=[["r"], ["g", "b"]])
    assert x._fmt == [["r"], ["g", "b"]]
    x.window.close()
    del x

    # invalid vector fmt for chan 2
    with pytest.raises(AssertionError):
        make_plot(chanlist, fmt=[["r"], ["g"]])

    # invalid channels fmt
    with pytest.raises(AssertionError):
        make_plot(chanlist, fmt=[["r"], ["g"], ["b"]])

    TriggerHandler.cls_cleanup()


def test_pluginplotpqg_attached_mode_surface() -> None:
    """Attached mode should expose widget without detached window."""
    chanlist = [DeviceChannel(chan=1, _type=2, vdim=2, name="chan1")]
    plot = make_plot(chanlist, mode="attached")

    assert plot.mode == EPlotMode.ATTACHED.value
    assert plot.window is None
    assert plot.widget is not None
    assert len(plot.plist) == 1

    plot.close()
    TriggerHandler.cls_cleanup()


def test_pluginplotpqg_close_closes_detached_window() -> None:
    """Detached close() should forward to the managed window."""
    chanlist = [DeviceChannel(chan=1, _type=2, vdim=1, name="chan1")]
    plot = make_plot(chanlist)

    plot.window.show()
    plot.close()

    TriggerHandler.cls_cleanup()


def test_build_plot_surface_delegates_to_factory(mocker) -> None:
    """build_plot_surface should normalize handler callbacks once."""
    handler = RecordingPluginHandler()
    surface = object()
    create = mocker.patch(
        "nxscli_pqg.plot_pqg.create_plot_surface", return_value=surface
    )

    out = build_plot_surface(
        handler,
        {
            "channels": [1, 2],
            "trig": ["always"],
            "dpi": 123,
            "fmt": ["r"],
            "plot_mode": "attached",
            "plot_parent": "parent",
        },
    )

    assert out is surface
    create.assert_called_once_with(
        chanlist=["chan-1", "chan-2"],
        trig=[("trig", ["chan-1", "chan-2"], ["always"])],
        cb=handler.cb,
        dpi=123,
        fmt=["r"],
        mode="attached",
        parent="parent",
    )


def test_private_build_plot_surface_delegates_to_factory(mocker) -> None:
    """Private build helper should normalize handler callbacks once."""
    handler = RecordingPluginHandler()
    surface = object()
    create = mocker.patch(
        "nxscli_pqg._plot_factory.create_plot_surface", return_value=surface
    )

    out = build_plot_surface_private(
        handler,
        {
            "channels": [1, 2],
            "trig": ["always"],
            "dpi": 123,
            "fmt": ["r"],
            "plot_mode": "attached",
            "plot_parent": "parent",
        },
    )

    assert out is surface
    create.assert_called_once_with(
        chanlist=["chan-1", "chan-2"],
        trig=[("trig", ["chan-1", "chan-2"], ["always"])],
        cb=handler.cb,
        dpi=123,
        fmt=["r"],
        mode="attached",
        parent="parent",
    )


def test_pluginplotpqg_vector_visibility_api() -> None:
    """Vector visibility helpers should match runtime-service expectations."""
    chanlist = [
        DeviceChannel(chan=1, _type=2, vdim=2, name="chan1"),
        DeviceChannel(chan=2, _type=2, vdim=1, name="chan2"),
    ]
    plot = make_plot(chanlist, mode="attached")
    states = plot.get_vector_states()

    assert [(state.channel, state.vector) for state in states] == [
        (1, 0),
        (1, 1),
        (2, 0),
    ]
    assert all(state.visible for state in states)

    plot.set_vector_visible(channel=1, vector=1, visible=False)
    states = plot.get_vector_states()
    hidden = [
        state for state in states if state.channel == 1 and state.vector == 1
    ]
    assert len(hidden) == 1
    assert hidden[0].visible is False

    with pytest.raises(ValueError, match="Invalid vector index"):
        plot.set_vector_visible(channel=1, vector=3, visible=False)

    with pytest.raises(ValueError, match="Channel 99 not found"):
        plot.set_vector_visible(channel=99, vector=0, visible=False)

    plot.close()
    TriggerHandler.cls_cleanup()


def test_pluginplotpqg_ani_clear_stops_handlers() -> None:
    """Animation cleanup should stop registered handlers in place."""
    chanlist = [DeviceChannel(chan=1, _type=2, vdim=1, name="chan1")]
    plot = make_plot(chanlist, mode="attached")

    class DummyAni:
        def __init__(self) -> None:
            self.stop_calls = 0

        def stop(self) -> None:
            self.stop_calls += 1

    ani1 = DummyAni()
    ani2 = DummyAni()
    plot.ani_append(ani1)  # type: ignore[arg-type]
    plot.ani_append(ani2)  # type: ignore[arg-type]

    plot.ani_clear()

    assert ani1.stop_calls == 1
    assert ani2.stop_calls == 1
    assert plot.ani == []

    plot.close()
    TriggerHandler.cls_cleanup()


def test_parse_format_string() -> None:
    """Test parse_format_string function."""
    # Valid format strings
    result = parse_format_string("r")
    assert result["color"] == "r"
    assert result["linestyle"] is None
    assert result["marker"] is None

    result = parse_format_string("r-")
    assert result["color"] == "r"
    assert result["linestyle"] == "-"
    assert result["marker"] is None

    result = parse_format_string("b--")
    assert result["color"] == "b"
    assert result["linestyle"] == "--"
    assert result["marker"] is None

    result = parse_format_string("g-.")
    assert result["color"] == "g"
    assert result["linestyle"] == "-."
    assert result["marker"] is None

    result = parse_format_string("y:")
    assert result["color"] == "y"
    assert result["linestyle"] == ":"
    assert result["marker"] is None

    result = parse_format_string("ro")
    assert result["color"] == "r"
    assert result["linestyle"] is None
    assert result["marker"] == "o"

    result = parse_format_string("bs")
    assert result["color"] == "b"
    assert result["linestyle"] is None
    assert result["marker"] == "s"

    result = parse_format_string("r-o")
    assert result["color"] == "r"
    assert result["linestyle"] == "-"
    assert result["marker"] == "o"

    result = parse_format_string("b--s")
    assert result["color"] == "b"
    assert result["linestyle"] == "--"
    assert result["marker"] == "s"

    result = parse_format_string("k-.+")
    assert result["color"] == "k"
    assert result["linestyle"] == "-."
    assert result["marker"] == "+"

    # Just linestyle (no color)
    result = parse_format_string("-")
    assert result["color"] is None
    assert result["linestyle"] == "-"
    assert result["marker"] is None

    # Just marker (no color, no linestyle)
    result = parse_format_string("o")
    assert result["color"] is None
    assert result["linestyle"] is None
    assert result["marker"] == "o"

    # Invalid format strings should raise ValueError
    with pytest.raises(ValueError, match="Invalid format string"):
        parse_format_string("rz")  # invalid marker

    with pytest.raises(ValueError, match="Invalid format string"):
        parse_format_string("abc")  # invalid characters

    with pytest.raises(ValueError, match="Invalid format string"):
        parse_format_string("123")  # no valid components


def test_plotdataaxespqg_invalid_format() -> None:
    """Test PlotDataAxesPqg with invalid format strings."""
    import pyqtgraph as pg

    PqgManager.get_app()

    plot_widget = pg.PlotWidget()
    chan = DeviceChannel(chan=0, _type=2, vdim=2, name="chan0")

    # Invalid format should raise ValueError (no longer caught internally)
    with pytest.raises(ValueError, match="Invalid format string"):
        PlotDataAxesPqg(plot_widget, chan, fmt=["rz", "b--"])

    plot_widget.close()


def test_parse_format_string_empty() -> None:
    """Test parse_format_string with empty string."""
    result = parse_format_string("")
    assert result["color"] is None
    assert result["linestyle"] is None
    assert result["marker"] is None


def test_parse_format_string_no_valid_components() -> None:
    """Test parse_format_string with string that has no valid components."""
    with pytest.raises(ValueError, match="unrecognized marker or character"):
        parse_format_string("xyz")


def test_plotdataaxespqg_format_branches() -> None:
    """Test PlotDataAxesPqg format parsing branches."""
    import pyqtgraph as pg

    PqgManager.get_app()

    plot_widget = pg.PlotWidget()
    chan = DeviceChannel(chan=0, _type=2, vdim=3, name="chan0")

    # Test with format that has no color (should use default color)
    x = PlotDataAxesPqg(plot_widget, chan, fmt=["-", "--", "-."])
    assert len(x.curves) == 3

    # Test with format that has linestyle
    x = PlotDataAxesPqg(plot_widget, chan, fmt=["r-", "b--", "g-."])
    assert len(x.curves) == 3

    # Test with format that has marker
    x = PlotDataAxesPqg(plot_widget, chan, fmt=["ro", "bs", "gd"])
    assert len(x.curves) == 3

    plot_widget.close()


def test_pluginanimationcommonpqg_fetch_data_numpy_fastpath() -> None:
    class FakeQueueData:
        vdim = 2

        def __init__(self) -> None:
            self._payloads = [
                [
                    DNxscopeStreamBlock(
                        data=np.array([[1, 2], [3, 4]]), meta=None
                    )
                ],
                [DNxscopeStreamBlock(data=np.empty((0, 2)), meta=None)],
                [DNxscopeStreamBlock(data=np.array([[5, 6]]), meta=None)],
                [],
            ]

        def queue_get(self, block: bool = False):  # noqa: ANN001, ARG002
            return self._payloads.pop(0)

    chan = DeviceChannel(chan=0, _type=2, vdim=2, name="chan0")
    qdata = FakeQueueData()
    ani = PluginAnimationCommonPqg(
        pdata=PlotDataCommon(chan),
        qdata=qdata,  # type: ignore[arg-type]
        write="",
    )
    xdata, ydata, trigger_x = ani._fetch_data()
    assert np.array_equal(xdata[0], np.array([0, 1, 2]))
    assert np.array_equal(xdata[1], np.array([0, 1, 2]))
    assert np.array_equal(ydata[0], np.array([1, 3, 5]))
    assert np.array_equal(ydata[1], np.array([2, 4, 6]))
    assert trigger_x is None


def test_pluginanimationcommonpqg_trim_and_hold_helpers() -> None:
    chan = DeviceChannel(chan=0, _type=2, vdim=1, name="chan0")
    ani = PluginAnimationCommonPqg(
        pdata=PlotDataCommon(chan),
        qdata=type("Q", (), {"vdim": 1})(),  # type: ignore[arg-type]
        write="",
        hold_after_trigger=True,
        hold_post_samples=4,
    )

    x1 = [np.array([10.0, 11.0, 12.0])]
    y1 = [np.array([1.0, 2.0, 3.0])]
    out1 = ani._trim_frame_for_hold(x1, y1, 10.5)
    assert np.array_equal(out1[0][0], np.array([10.0, 11.0, 12.0]))
    assert ani._hold_ready(12.0) is False
    assert ani._hold_ready(None) is False

    x2 = [np.array([10.0, 11.0, 12.0, 13.0, 14.0, 15.0])]
    y2 = [np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])]
    out2 = ani._trim_frame_for_hold(x2, y2, None)
    assert np.array_equal(out2[0][0], np.array([10.0, 11.0, 12.0, 13.0, 14.0]))
    assert np.array_equal(out2[1][0], np.array([1.0, 2.0, 3.0, 4.0, 5.0]))
    assert ani._hold_ready(14.0) is True


def test_fetch_animation_data_stops_after_first_trigger_batch() -> None:
    class FakeQueueData:
        vdim = 1

        def __init__(self) -> None:
            self._payloads = [
                [
                    DNxscopeStreamBlock(
                        data=np.array([[1.0], [2.0]]),
                        meta=None,
                    )
                ],
                [
                    DNxscopeStreamBlock(
                        data=np.array([[3.0], [4.0]]),
                        meta=None,
                    )
                ],
            ]
            self._events = [
                type(
                    "Event",
                    (),
                    {
                        "sample_index": 2.0,
                        "channel": 7,
                        "capture_mode": "start_after",
                    },
                )(),
                None,
            ]

        def queue_get(self, block: bool = False):  # noqa: ANN001, ARG002
            if not self._payloads:
                return []
            return self._payloads.pop(0)

        def pop_trigger_event(self):  # noqa: ANN001
            if not self._events:
                return None
            return self._events.pop(0)

    qdata = FakeQueueData()
    xdata, ydata, next_count, trigger_x = fetch_animation_data(
        qdata,
        count=10,
        stop_on_trigger=True,
    )

    assert next_count == 12
    assert trigger_x == 12.0
    assert np.array_equal(xdata[0], np.array([10, 11]))
    assert np.array_equal(ydata[0], np.array([1.0, 2.0]))
    remaining = qdata.queue_get(block=False)
    assert len(remaining) == 1
    assert np.array_equal(remaining[0].data, np.array([[3.0], [4.0]]))
    assert qdata.queue_get(block=False) == []
    assert qdata.pop_trigger_event() is None
    assert qdata.pop_trigger_event() is None


def test_pluginanimationcommonpqg_rejects_non_block_payload() -> None:
    class Sample:
        def __init__(self, data):  # noqa: ANN001
            self.data = data

    class FakeQueueData:
        vdim = 1

        def __init__(self) -> None:
            self._payloads = [[Sample((9,))], []]

        def queue_get(self, block: bool = False):  # noqa: ANN001, ARG002
            if not self._payloads:
                return []
            return self._payloads.pop(0)

    chan = DeviceChannel(chan=0, _type=2, vdim=1, name="chan0")
    qdata = FakeQueueData()
    ani = PluginAnimationCommonPqg(
        pdata=PlotDataCommon(chan),
        qdata=qdata,  # type: ignore[arg-type]
        write="",
    )
    with pytest.raises(RuntimeError):
        _ = ani._fetch_data()
    qdata._payloads = []
    assert qdata.queue_get(block=False) == []


def test_pluginanimationcommonpqg_rejects_non_list_payload() -> None:
    class FakeQueueData:
        vdim = 1

        def queue_get(self, block: bool = False):  # noqa: ANN001, ARG002
            return "bad"

    chan = DeviceChannel(chan=0, _type=2, vdim=1, name="chan0")
    qdata = FakeQueueData()
    ani = PluginAnimationCommonPqg(
        pdata=PlotDataCommon(chan),
        qdata=qdata,  # type: ignore[arg-type]
        write="",
    )
    with pytest.raises(RuntimeError):
        _ = ani._fetch_data()


def test_pluginanimationcommonpqg_fetch_data_numpy_loop_limit() -> None:
    class FakeQueueData:
        vdim = 1

        def queue_get(self, block: bool = False):  # noqa: ANN001, ARG002
            return [DNxscopeStreamBlock(data=np.array([[1]]), meta=None)]

    chan = DeviceChannel(chan=0, _type=2, vdim=1, name="chan0")
    qdata = FakeQueueData()
    ani = PluginAnimationCommonPqg(
        pdata=PlotDataCommon(chan),
        qdata=qdata,  # type: ignore[arg-type]
        write="",
    )
    xdata, ydata, trigger_x = ani._fetch_data()
    assert len(xdata[0]) == 100
    assert len(ydata[0]) == 100
    assert trigger_x is None


def test_pluginplotpqg_attached_mode_and_vector_controls() -> None:
    chanlist = [DeviceChannel(chan=1, _type=2, vdim=2, name="chan1")]
    dtc = DTriggerConfig(ETriggerType.ALWAYS_OFF)
    trig = [TriggerHandler(1, dtc)]
    cb = PluginDataCb(dummy_stream_sub, dummy_stream_unsub)
    x = PluginPlotPqg(chanlist, trig, cb, mode="attached")

    assert x.window is None
    assert x.widget is not None
    assert x.mode == "attached"

    states = x.get_vector_states()
    assert len(states) == 2
    assert states[0].channel == 1

    x.set_vector_visible(1, 0, False)
    x.set_vector_visible(1, 0, True)
    with pytest.raises(ValueError):
        x.set_vector_visible(1, -1, True)
    with pytest.raises(ValueError):
        x.set_vector_visible(9, 0, True)

    x.close()
    TriggerHandler.cls_cleanup()


def test_plot_mode_parse_and_factory() -> None:
    assert EPlotMode.from_text("attached") is EPlotMode.ATTACHED
    assert EPlotMode.from_text("unknown") is EPlotMode.DETACHED

    chanlist = [DeviceChannel(chan=1, _type=2, vdim=1, name="chan1")]
    dtc = DTriggerConfig(ETriggerType.ALWAYS_OFF)
    trig = [TriggerHandler(1, dtc)]
    cb = PluginDataCb(dummy_stream_sub, dummy_stream_unsub)
    plot = create_plot_surface(chanlist, trig, cb, mode="attached")
    assert isinstance(plot, PluginPlotPqg)
    assert plot.mode == "attached"
    plot.close()
    TriggerHandler.cls_cleanup()
