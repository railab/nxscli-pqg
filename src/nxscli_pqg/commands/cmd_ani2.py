"""Module containing animation2 plugin command."""

from typing import TYPE_CHECKING

import click
from nxscli.cli.environment import Environment, pass_environment

from nxscli_pqg.cli.types import plot_options
from nxscli_pqg.commands._common import enable_plot_command

if TYPE_CHECKING:
    from nxscli.trigger import DTriggerConfigReq


###############################################################################
# Command: cmd_pani2
###############################################################################


@click.command(name="q_roll")
@click.argument("maxsamples", type=int, required=True)
@click.option(
    "--hold-post-samples",
    type=int,
    default=0,
    show_default=True,
    help="Keep updating this many samples after the trigger before hold.",
)
@plot_options
@pass_environment
def cmd_pani2(
    ctx: Environment,
    maxsamples: int,
    hold_post_samples: int,
    chan: list[int],
    trig: dict[int, "DTriggerConfigReq"],
    dpi: float,
    hold_after_trigger: bool,
    fmt: list[list[str]],
    write: str,
) -> bool:
    """[plugin] Animation plot with a lenght limit (saturated X-axis).

    Keyboard shortcuts:
    - 'f' or 'F': toggle fullscreen
    - 'q', 'Q', or Escape: close window
    """
    return enable_plot_command(
        ctx,
        "q_roll",
        maxsamples=maxsamples,
        channels=chan,
        trig=trig,
        dpi=dpi,
        hold_after_trigger=hold_after_trigger,
        hold_post_samples=hold_post_samples,
        fmt=fmt,
        write=write,
    )
