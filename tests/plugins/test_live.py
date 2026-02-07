"""Tests for animation1 plugin."""

from unittest.mock import Mock

import numpy as np

from nxscli_pqg.plugins.live import LiveAnimation, PluginLive


def test_pluginanimaton1_init() -> None:
    """Test PluginLive initialization."""
    plugin = PluginLive()

    assert plugin.stream is True


def test_live_animation_init_configures_axes() -> None:
    """Live animation should enable dynamic x-scaling and initial y range."""

    class DummyPData:
        def __init__(self) -> None:
            self.enable_auto_range = Mock()
            self.set_ylim = Mock()

    pdata = DummyPData()
    ani = LiveAnimation(pdata, Mock(vdim=1), "")

    assert ani._plot_data is pdata
    pdata.enable_auto_range.assert_called_once_with(x=True, y=False)
    pdata.set_ylim.assert_called_once_with((0.0, 1.0))


def test_pluginanimaton1_start_returns_live_animation() -> None:
    """PluginLive should build the backend animation with write path."""
    plugin = PluginLive()

    class DummyPData:
        def enable_auto_range(self, *, x: bool, y: bool) -> None:
            self.range_args = (x, y)

        def set_ylim(self, ylim) -> None:
            self.ylim = ylim

    pdata = DummyPData()
    qdata = object()

    ani = plugin._start(pdata, qdata, {"write": ""})

    assert isinstance(ani, LiveAnimation)
    assert ani._plot_data is pdata
    assert ani._queue_data is qdata
    assert ani._write == ""


def test_pluginanimaton1_start_passes_hold_after_trigger() -> None:
    class DummyPData:
        def enable_auto_range(self, *, x: bool, y: bool) -> None:
            self.range_args = (x, y)

        def set_ylim(self, ylim) -> None:
            self.ylim = ylim

    ani = PluginLive()._start(
        DummyPData(),
        object(),
        {"write": "", "hold_after_trigger": True},
    )

    assert ani._hold_after_trigger is True


def test_live_animation_update_accepts_numpy_series() -> None:
    """LiveAnimation should handle ndarray-backed frame data."""

    class DummyCurve:
        def __init__(self) -> None:
            self.setData = Mock()

    class DummyPData:
        def __init__(self) -> None:
            self.enable_auto_range = Mock()
            self.set_ylim = Mock()
            self.xdata = [[], []]
            self.ydata = [[], []]
            self.curves = [DummyCurve(), DummyCurve()]
            self.trigger_line = Mock()

        def xdata_extend(self, data) -> None:  # noqa: ANN001
            for i, series in enumerate(data):
                self.xdata[i].extend(series.tolist())

        def ydata_extend(self, data) -> None:  # noqa: ANN001
            for i, series in enumerate(data):
                self.ydata[i].extend(series.tolist())

        def set_trigger_marker(self, xpos) -> None:  # noqa: ANN001
            self.trigger_x = xpos

    pdata = DummyPData()
    ani = LiveAnimation(pdata, Mock(vdim=2), "")

    ani._animation_update(
        [np.array([0, 1]), np.array([0, 1])],
        [np.array([1.0, 3.0]), np.array([2.0, 4.0])],
    )

    assert pdata.xdata == [[0, 1], [0, 1]]
    assert pdata.ydata == [[1.0, 3.0], [2.0, 4.0]]
    pdata.curves[0].setData.assert_called_once_with([0, 1], [1.0, 3.0])
    pdata.curves[1].setData.assert_called_once_with([0, 1], [2.0, 4.0])
    pdata.set_ylim.assert_any_call((0.0, 1.0))


def test_live_animation_update_ylim_accepts_numpy_series() -> None:
    """LiveAnimation y-range update should not rely on list truthiness."""

    class DummyPData:
        def __init__(self) -> None:
            self.enable_auto_range = Mock()
            self.set_ylim = Mock()
            self.trigger_line = Mock()

        def set_trigger_marker(self, xpos) -> None:  # noqa: ANN001
            self.trigger_x = xpos

    pdata = DummyPData()
    ani = LiveAnimation(pdata, Mock(vdim=2), "")
    pdata.set_trigger_marker(3)

    ani._update_ylim([np.array([1.0, 3.0]), np.array([2.0, 4.0])])

    assert pdata.trigger_x == 3
    pdata.set_ylim.assert_any_call((0.0, 1.0))
    assert pdata.set_ylim.call_count >= 2


def test_live_animation_holds_after_trigger_event(mocker) -> None:
    ani = LiveAnimation(Mock(), Mock(vdim=1), "", hold_after_trigger=True)
    ani._running = True
    ani._fetch_data = Mock(
        return_value=(
            [np.array([0, 1])],
            [np.array([1.0, 2.0])],
            1.0,
        )
    )  # type: ignore[method-assign]
    ani._animation_update = Mock()
    stop = mocker.patch.object(ani, "stop")

    ani._on_timer()

    ani._animation_update.assert_called_once()
    stop.assert_called_once_with()


def test_live_animation_skip_hold_without_trigger(mocker) -> None:
    ani = LiveAnimation(Mock(), Mock(vdim=1), "", hold_after_trigger=True)
    stop = mocker.patch.object(ani, "stop")

    ani._hold_on_trigger([[]], None)

    stop.assert_not_called()


def test_live_animation_waits_for_hold_post_samples(mocker) -> None:
    ani = LiveAnimation(
        Mock(),
        Mock(vdim=1),
        "",
        hold_after_trigger=True,
        hold_post_samples=4,
    )
    stop = mocker.patch.object(ani, "stop")

    ani._hold_on_trigger([[1.0, 2.0, 3.0]], 1.0)
    stop.assert_not_called()

    ani._hold_on_trigger([[1.0, 2.0, 3.0, 4.0, 5.0]], None)
    stop.assert_called_once_with()


def test_live_animation_hold_post_waits_for_non_empty_xdata(mocker) -> None:
    ani = LiveAnimation(
        Mock(),
        Mock(vdim=1),
        "",
        hold_after_trigger=True,
        hold_post_samples=4,
    )
    stop = mocker.patch.object(ani, "stop")

    ani._hold_on_trigger([], 1.0)

    stop.assert_not_called()


def test_live_animation_skip_hold_when_already_held(mocker) -> None:
    ani = LiveAnimation(Mock(), Mock(vdim=1), "", hold_after_trigger=True)
    stop = mocker.patch.object(ani, "stop")
    ani._held_on_trigger = True

    ani._hold_on_trigger([[1.0]], 1.0)

    stop.assert_not_called()
