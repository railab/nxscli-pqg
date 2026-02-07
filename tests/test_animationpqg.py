"""Tests for animation_pqg module."""

import pytest

from nxscli_pqg.animation_pqg import IPluginAnimation
from tests.helpers import (
    DummyAni,
    FakePlot,
    FakePluginHandler,
    make_plot_kwargs,
)


class XTestPluginAnimation(IPluginAnimation):
    """Test plugin animation class."""

    def __init__(self) -> None:
        """Initialize test plugin animation."""
        super().__init__()

    def _start(self, pdata, qdata, kwargs):
        """Start animation."""
        return DummyAni()  # type: ignore[return-value]


def test_ipluginanimation_init() -> None:
    """Test IPluginAnimation initialization."""
    # abstract class
    with pytest.raises(TypeError):
        IPluginAnimation()

    x = XTestPluginAnimation()

    # phandler not connected
    with pytest.raises(AttributeError):
        x.start(None)
    with pytest.raises(AttributeError):
        x.result()
    with pytest.raises(AttributeError):
        x.clear()
    with pytest.raises(AttributeError):
        x.stop()

    assert x.stream is True
    assert x.data_wait() is True
    assert x.get_plot_handler() is None

    x.connect_phandler(FakePluginHandler())


def test_ipluginanimation_start_nochannels(mocker) -> None:
    """Test IPluginAnimation start with no channels."""
    x = XTestPluginAnimation()
    x.connect_phandler(FakePluginHandler())
    mocker.patch(
        "nxscli_pqg.animation_pqg.build_plot_surface", return_value=FakePlot()
    )
    show = mocker.patch("nxscli_pqg.animation_pqg.PqgManager.show")

    # start
    args = make_plot_kwargs(channels=[], fmt="", write="")
    assert x.start(args) is True

    # clear
    x.clear()

    # result
    x.result()
    show.assert_called_once_with(block=False)

    # stop
    x.stop()


def test_ipluginanimation_start(mocker) -> None:
    """Test IPluginAnimation start with channels."""
    x = XTestPluginAnimation()
    x.connect_phandler(FakePluginHandler())
    plot = FakePlot()
    mocker.patch(
        "nxscli_pqg.animation_pqg.build_plot_surface", return_value=plot
    )

    # start
    args = make_plot_kwargs()
    assert x.start(args) is True

    # get_plot_handler returns the PluginPlotPqg after start
    assert x.get_plot_handler() is plot

    # clear
    x.clear()

    # result
    x.result()

    # stop
    x.stop()


def test_ipluginanimation_result_attached(mocker) -> None:
    """Test IPluginAnimation result in attached plot mode."""
    x = XTestPluginAnimation()
    x.connect_phandler(FakePluginHandler())
    plot = FakePlot(mode="attached")
    mocker.patch(
        "nxscli_pqg.animation_pqg.build_plot_surface", return_value=plot
    )
    show = mocker.patch("nxscli_pqg.animation_pqg.PqgManager.show")

    args = make_plot_kwargs(plot_mode="attached")
    assert x.start(args) is True
    ret = x.result()
    assert ret is plot
    assert ret.window is None
    show.assert_not_called()
    x.stop()


def test_ipluginanimation_get_inputhook() -> None:
    """Test IPluginAnimation get_inputhook method."""
    # Get the inputhook
    hook = IPluginAnimation.get_inputhook()

    # Should return a callable function
    assert hook is not None
    assert callable(hook)

    # Test calling the hook (should not raise)
    hook(None)


def test_ipluginanimation_start_does_not_show_before_result(mocker) -> None:
    x = XTestPluginAnimation()
    x.connect_phandler(FakePluginHandler())
    plot = FakePlot()
    mocker.patch(
        "nxscli_pqg.animation_pqg.build_plot_surface", return_value=plot
    )
    show = mocker.patch("nxscli_pqg.animation_pqg.PqgManager.show")

    args = make_plot_kwargs(hold_after_trigger=True)
    assert x.start(args) is True
    show.assert_not_called()

    x.result()
    show.assert_called_once_with(block=False)
