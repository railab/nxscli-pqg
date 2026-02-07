"""Tests for animation2 plugin."""

from unittest.mock import Mock

import numpy as np

from nxscli_pqg.plugins.roll import PluginRoll, RollAnimation


def test_pluginanimaton2_init() -> None:
    """Test PluginRoll initialization."""
    plugin = PluginRoll()

    assert plugin.stream is True


def test_roll_animation_init_configures_static_axes() -> None:
    """Roll animation should disable autorange and set initial y limits."""

    class DummyPData:
        def __init__(self) -> None:
            self.enable_auto_range = Mock()
            self.set_ylim = Mock()

    pdata = DummyPData()
    ani = RollAnimation(pdata, Mock(vdim=1), "", static_xticks=False)

    assert ani._plot_data is pdata
    assert ani._static_xticks is False
    pdata.enable_auto_range.assert_called_once_with(x=False, y=False)
    pdata.set_ylim.assert_called_once_with((0.0, 1.0))


def test_pluginanimaton2_start_sets_window_and_returns_roll_animation() -> (
    None
):
    """PluginRoll should cap samples before building the animation."""

    class DummyPData:
        def __init__(self) -> None:
            self.samples_max = 0
            self.set_xlim = Mock()
            self.enable_auto_range = Mock()
            self.set_ylim = Mock()

    plugin = PluginRoll()
    pdata = DummyPData()
    qdata = object()

    ani = plugin._start(
        pdata,
        qdata,
        {
            "maxsamples": 32,
            "write": "out.gif",
            "hold_after_trigger": False,
        },
    )

    assert isinstance(ani, RollAnimation)
    assert pdata.samples_max == 32
    pdata.set_xlim.assert_called_once_with((0, 32))
    assert ani._queue_data is qdata
    assert ani._write == "out.gif"


def test_pluginanimaton2_start_passes_hold_after_trigger() -> None:
    class DummyPData:
        def __init__(self) -> None:
            self.samples_max = 0
            self.set_xlim = Mock()
            self.enable_auto_range = Mock()
            self.set_ylim = Mock()

    ani = PluginRoll()._start(
        DummyPData(),
        object(),
        {"maxsamples": 32, "write": "", "hold_after_trigger": True},
    )

    assert ani._hold_after_trigger is True


def test_roll_animation_static_update_accepts_numpy_series() -> None:
    """RollAnimation static path should handle ndarray-backed frame data."""

    class DummyCurve:
        def __init__(self) -> None:
            self.setData = Mock()

    class DummyPData:
        def __init__(self) -> None:
            self.samples_max = 1
            self.enable_auto_range = Mock()
            self.set_ylim = Mock()
            self.xdata = [[], []]
            self.ydata = [[], []]
            self.curves = [DummyCurve(), DummyCurve()]
            self.trigger_line = Mock()

        def xdata_extend_max(self, data) -> None:  # noqa: ANN001
            self.xdata[0].extend(data[0].tolist())
            self.xdata[1].extend(data[1].tolist())
            remove0 = len(self.xdata[0]) - self.samples_max
            remove1 = len(self.xdata[1]) - self.samples_max
            self.xdata[0] = self.xdata[0][max(remove0, 0) :]
            self.xdata[1] = self.xdata[1][max(remove1, 0) :]

        def ydata_extend_max(self, data) -> None:  # noqa: ANN001
            self.ydata[0].extend(data[0].tolist())
            self.ydata[1].extend(data[1].tolist())
            remove0 = len(self.ydata[0]) - self.samples_max
            remove1 = len(self.ydata[1]) - self.samples_max
            self.ydata[0] = self.ydata[0][max(remove0, 0) :]
            self.ydata[1] = self.ydata[1][max(remove1, 0) :]

        def set_trigger_marker(self, xpos) -> None:  # noqa: ANN001
            self.trigger_x = xpos

    pdata = DummyPData()
    ani = RollAnimation(pdata, Mock(vdim=2), "", static_xticks=True)

    ani._animation_update(
        [np.array([0, 1]), np.array([0, 1])],
        [np.array([1.0, 3.0]), np.array([2.0, 4.0])],
    )

    assert pdata.xdata == [[1], [1]]
    assert pdata.ydata == [[3.0], [4.0]]
    pdata.curves[0].setData.assert_called_once_with([0], [3.0])
    pdata.curves[1].setData.assert_called_once_with([0], [4.0])
    pdata.set_ylim.assert_any_call((0.0, 1.0))


def test_roll_animation_update_ylim_accepts_numpy_series() -> None:
    """RollAnimation y-range update should not use ndarray truthiness."""

    class DummyPData:
        def __init__(self) -> None:
            self.enable_auto_range = Mock()
            self.set_ylim = Mock()
            self.trigger_line = Mock()

        def set_trigger_marker(self, xpos) -> None:  # noqa: ANN001
            self.trigger_x = xpos

    pdata = DummyPData()
    ani = RollAnimation(pdata, Mock(vdim=2), "", static_xticks=False)
    pdata.set_trigger_marker(4)

    ani._update_ylim([np.array([1.0, 3.0]), np.array([2.0, 4.0])])

    assert pdata.trigger_x == 4
    pdata.set_ylim.assert_any_call((0.0, 1.0))
    assert pdata.set_ylim.call_count >= 2


def test_roll_animation_static_update_hides_trigger_line_without_event() -> (
    None
):
    """RollAnimation should hide the marker when no trigger event exists."""

    class DummyCurve:
        def __init__(self) -> None:
            self.setData = Mock()

    class DummyPData:
        def __init__(self) -> None:
            self.samples_max = 8
            self.enable_auto_range = Mock()
            self.set_ylim = Mock()
            self.xdata = [[]]
            self.ydata = [[]]
            self.curves = [DummyCurve()]
            self.trigger_line = Mock()

        def xdata_extend_max(self, data) -> None:  # noqa: ANN001
            self.xdata[0].extend(data[0].tolist())

        def ydata_extend_max(self, data) -> None:  # noqa: ANN001
            self.ydata[0].extend(data[0].tolist())

        def set_trigger_marker(self, xpos) -> None:  # noqa: ANN001
            self.trigger_x = xpos

    pdata = DummyPData()
    ani = RollAnimation(pdata, Mock(vdim=1), "", static_xticks=True)

    ani._animation_update(
        [np.array([0, 1, 2])],
        [np.array([1.0, 2.0, 3.0])],
        None,
    )

    assert pdata.trigger_x is None
    pdata.trigger_line.hide.assert_called()


def test_roll_animation_holds_after_trigger_event(mocker) -> None:
    ani = RollAnimation(Mock(), Mock(vdim=1), "", hold_after_trigger=True)
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
