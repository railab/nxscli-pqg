"""Module containing captgure plugin command."""

from typing import TYPE_CHECKING

import click
from nxscli.cli.environment import Environment, pass_environment
from nxscli.cli.types import Samples

from nxscli_pqg.cli.types import plot_options
from nxscli_pqg.commands._common import enable_plot_command

if TYPE_CHECKING:
    from nxscli.trigger import DTriggerConfigReq


###############################################################################
# Command: cmd_pcap
###############################################################################


@click.command(name="q_snap")
@click.argument("samples", type=Samples(), required=True)
@plot_options
@pass_environment
def cmd_pcap(
    ctx: Environment,
    samples: int,
    chan: list[int],
    trig: dict[int, "DTriggerConfigReq"],
    dpi: float,
    hold_after_trigger: bool,
    fmt: list[list[str]],
    write: str,
) -> bool:
    """[plugin] Static plot for a given number of samples.

    If SAMPLES argument is set to 'i' then we capture data until enter
    is press.

    Keyboard shortcuts:
    - 'f' or 'F': toggle fullscreen
    - 'q', 'Q', or Escape: close window
    """  # noqa: D301
    del hold_after_trigger
    return enable_plot_command(
        ctx,
        "q_snap",
        samples=samples,
        channels=chan,
        trig=trig,
        dpi=dpi,
        fmt=fmt,
        write=write,
    )
