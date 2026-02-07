import nxscli
import pytest  # type: ignore
from click.testing import CliRunner
from nxscli.cli.main import main


@pytest.fixture
def enable_plugin(mocker):
    return mocker.patch(
        "nxscli.phandler.PluginHandler.enable",
        autospec=True,
        return_value=True,
    )


@pytest.fixture
def runner(mocker, enable_plugin):
    mocker.patch.object(nxscli.cli.main, "wait_for_plugins", autospec=True)
    return CliRunner()


def test_main_pqg(runner):
    args = ["dummy", "pqg"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0


def test_main_q_snap(runner):
    args = ["chan", "1", "q_snap", "1"]
    result = runner.invoke(main, args)
    assert result.exit_code == 2

    # args = ["dummy", "q_snap", "1"]
    # result = runner.invoke(main, args)
    # assert result.exit_code == 1

    args = ["dummy", "chan", "1", "q_snap", "1"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0

    args = ["dummy", "chan", "1", "q_snap", "1000"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0


def test_main_q_live(runner):
    args = ["chan", "1", "q_live"]
    result = runner.invoke(main, args)
    assert result.exit_code == 2

    args = ["dummy", "1", "q_live"]
    result = runner.invoke(main, args)
    assert result.exit_code == 2

    args = ["dummy", "chan", "1", "q_live"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0


def test_main_q_live_hold_after_trigger_option(runner, enable_plugin):
    patched = enable_plugin
    args = ["dummy", "chan", "1", "q_live", "--hold-after-trigger"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0
    assert patched.call_args.kwargs["hold_after_trigger"] is True


def test_main_q_roll(runner):
    args = ["chan", "1", "q_roll", "1"]
    result = runner.invoke(main, args)
    assert result.exit_code == 2

    # args = ["dummy", "q_roll", "1"]
    # result = runner.invoke(main, args)
    # assert result.exit_code == 1

    args = ["dummy", "chan", "1", "q_roll"]
    result = runner.invoke(main, args)
    assert result.exit_code == 2

    args = ["dummy", "chan", "1", "q_roll", "1"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0


def test_main_pqfft(runner):
    args = ["chan", "1", "q_fft", "1"]
    result = runner.invoke(main, args)
    assert result.exit_code == 2

    args = ["dummy", "chan", "11", "q_fft", "1"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0


def test_main_pqhist(runner):
    args = ["chan", "1", "q_hist", "1"]
    result = runner.invoke(main, args)
    assert result.exit_code == 2

    args = ["dummy", "chan", "13", "q_hist", "--bins", "16", "1"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0


def test_main_pqxy(runner):
    args = ["chan", "1", "q_xy", "1"]
    result = runner.invoke(main, args)
    assert result.exit_code == 2

    args = ["dummy", "chan", "15,16", "q_xy", "1"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0

    args = ["dummy", "chan", "15", "q_xy", "1"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0


def test_main_pqfft_stream(runner):
    args = ["chan", "1", "q_fft_live", "128"]
    result = runner.invoke(main, args)
    assert result.exit_code == 2

    args = ["dummy", "chan", "11", "q_fft_live", "128"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0


def test_main_pqhist_stream(runner):
    args = ["chan", "1", "q_hist_live", "128"]
    result = runner.invoke(main, args)
    assert result.exit_code == 2

    args = ["dummy", "chan", "13", "q_hist_live", "--bins", "16", "128"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0


def test_main_pqxy_stream(runner):
    args = ["chan", "1", "q_xy_live", "128"]
    result = runner.invoke(main, args)
    assert result.exit_code == 2

    args = ["dummy", "chan", "15,16", "q_xy_live", "128"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0

    args = ["dummy", "chan", "15", "q_xy_live", "128"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0


def test_main_qpolar(runner):
    args = ["chan", "1", "q_polar", "1"]
    result = runner.invoke(main, args)
    assert result.exit_code == 2

    args = ["dummy", "chan", "0,2", "q_polar", "1"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0

    args = ["dummy", "chan", "16", "q_polar", "1"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0


def test_main_qpolar_stream(runner):
    args = ["chan", "1", "q_polar_live", "128"]
    result = runner.invoke(main, args)
    assert result.exit_code == 2

    args = ["dummy", "chan", "0,2", "q_polar_live", "128"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0

    args = ["dummy", "chan", "16", "q_polar_live", "128"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0


def test_main_dispatch_qfft_special_channel(runner, enable_plugin):
    patched = enable_plugin
    args = ["dummy", "chan", "11", "q_fft", "64"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0
    assert patched.call_count == 1
    assert patched.call_args.args[1] == "q_fft"
    assert patched.call_args.kwargs["channels"] is None


def test_main_dispatch_qhist_special_channel(runner, enable_plugin):
    patched = enable_plugin
    args = ["dummy", "chan", "13", "q_hist_live", "--bins", "16", "64"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0
    assert patched.call_count == 1
    assert patched.call_args.args[1] == "q_hist_live"
    assert patched.call_args.kwargs["channels"] is None


def test_main_dispatch_qxy_special_channels(runner, enable_plugin):
    patched = enable_plugin
    args = ["dummy", "chan", "15,16", "q_xy_live", "64"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0
    assert patched.call_count == 1
    assert patched.call_args.args[1] == "q_xy_live"
    assert patched.call_args.kwargs["channels"] is None


def test_main_dispatch_q_snap_interactive(runner, enable_plugin):
    patched = enable_plugin
    args = ["dummy", "chan", "1", "q_snap", "i"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0
    assert patched.call_count == 1
    assert patched.call_args.args[1] == "q_snap"
    assert patched.call_args.kwargs["samples"] == -1
    assert patched.call_args.kwargs["nostop"] is False


def test_main_trig_pqg(runner):
    args = ["dummy", "chan", "1", "trig", "xxx", "q_roll", "1"]
    result = runner.invoke(main, args)
    assert result.exit_code == 1

    args = ["dummy", "chan", "1", "trig", "x=1", "q_roll", "1"]
    result = runner.invoke(main, args)
    assert result.exit_code == 1

    args = ["dummy", "chan", "1", "trig", "g=1", "q_roll", "1"]
    result = runner.invoke(main, args)
    assert result.exit_code == 1

    args = ["dummy", "chan", "1", "trig", "g:on", "q_roll", "1"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0

    args = ["dummy", "chan", "1", "trig", "g:off", "q_roll", "1"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0

    args = ["dummy", "chan", "1,2", "trig", "1:on;2:off", "q_roll", "1"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0

    args = ["dummy", "chan", "1,2,3", "q_roll", "--trig", "2:off", "1"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0

    args = [
        "dummy",
        "chan",
        "1,2,3",
        "trig",
        "g:er#2@0,0,10,100",
        "q_snap",
        "100",
    ]
    result = runner.invoke(main, args)
    assert result.exit_code == 0
