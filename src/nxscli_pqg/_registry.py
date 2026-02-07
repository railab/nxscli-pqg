"""Private backend registry definitions."""

from typing import TYPE_CHECKING

from nxscli.iplugin import DPluginDescription

from nxscli_pqg.commands.cmd_ani1 import cmd_pani1
from nxscli_pqg.commands.cmd_ani2 import cmd_pani2
from nxscli_pqg.commands.cmd_cap import cmd_pcap
from nxscli_pqg.commands.cmd_fft import cmd_pqfft
from nxscli_pqg.commands.cmd_fft_stream import cmd_pqfft_stream
from nxscli_pqg.commands.cmd_hist import cmd_pqhist
from nxscli_pqg.commands.cmd_hist_stream import cmd_pqhist_stream
from nxscli_pqg.commands.cmd_polar import cmd_qpolar
from nxscli_pqg.commands.cmd_polar_stream import cmd_qpolar_stream
from nxscli_pqg.commands.cmd_xy import cmd_pqxy
from nxscli_pqg.commands.cmd_xy_stream import cmd_pqxy_stream
from nxscli_pqg.commands.config.cmd_pqg import cmd_pqg
from nxscli_pqg.plugins._typed_windowed import (
    PluginFftStream,
    PluginHistStream,
    PluginPolarStream,
    PluginXyStream,
)
from nxscli_pqg.plugins.fft import PluginFft
from nxscli_pqg.plugins.histogram import PluginHistogram
from nxscli_pqg.plugins.live import PluginLive
from nxscli_pqg.plugins.polar import PluginPolar
from nxscli_pqg.plugins.roll import PluginRoll
from nxscli_pqg.plugins.snap import PluginSnap
from nxscli_pqg.plugins.xy import PluginXy

if TYPE_CHECKING:
    import click
    from nxscli.iplugin import IPlugin


COMMANDS: tuple["click.Command", ...] = (
    cmd_pqg,
    cmd_pcap,
    cmd_pani1,
    cmd_pani2,
    cmd_pqfft,
    cmd_pqhist,
    cmd_pqxy,
    cmd_qpolar,
    cmd_pqfft_stream,
    cmd_pqhist_stream,
    cmd_pqxy_stream,
    cmd_qpolar_stream,
)

PLUGIN_TYPES: tuple[tuple[str, type["IPlugin"]], ...] = (
    ("q_snap", PluginSnap),
    ("q_live", PluginLive),
    ("q_roll", PluginRoll),
    ("q_fft", PluginFft),
    ("q_hist", PluginHistogram),
    ("q_xy", PluginXy),
    ("q_polar", PluginPolar),
    ("q_fft_live", PluginFftStream),
    ("q_hist_live", PluginHistStream),
    ("q_xy_live", PluginXyStream),
    ("q_polar_live", PluginPolarStream),
)


def build_commands_list() -> list["click.Command"]:
    """Return the exported backend command list."""
    return list(COMMANDS)


def build_plugins_list() -> list[DPluginDescription]:
    """Return the exported backend plugin list."""
    return [DPluginDescription(name, plugin) for name, plugin in PLUGIN_TYPES]
