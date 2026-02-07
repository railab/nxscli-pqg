import nxscli_pqg
import nxscli_pqg.ext_commands
import nxscli_pqg.ext_plugins


def test_nxsclipqg():
    assert nxscli_pqg.__version__

    assert isinstance(nxscli_pqg.ext_plugins.plugins_list, list)
    assert isinstance(nxscli_pqg.ext_commands.commands_list, list)
    assert [cmd.name for cmd in nxscli_pqg.ext_commands.commands_list] == [
        "pqg",
        "q_snap",
        "q_live",
        "q_roll",
        "q_fft",
        "q_hist",
        "q_xy",
        "q_polar",
        "q_fft_live",
        "q_hist_live",
        "q_xy_live",
        "q_polar_live",
    ]
    assert [plugin.name for plugin in nxscli_pqg.ext_plugins.plugins_list] == [
        "q_snap",
        "q_live",
        "q_roll",
        "q_fft",
        "q_hist",
        "q_xy",
        "q_polar",
        "q_fft_live",
        "q_hist_live",
        "q_xy_live",
        "q_polar_live",
    ]
