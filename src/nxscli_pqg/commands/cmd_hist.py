"""Module containing histogram plugin command."""

from typing import TYPE_CHECKING

import click
from nxscli.cli.environment import Environment, pass_environment
from nxscli.cli.types import Samples

from nxscli_pqg.cli.types import plot_options
from nxscli_pqg.commands._common import enable_plot_command

if TYPE_CHECKING:
    from nxscli.trigger import DTriggerConfigReq


@click.command(name="q_hist")
@click.argument("samples", type=Samples(), required=True)
@click.option("--bins", type=int, default=32, show_default=True)
@plot_options
@pass_environment
def cmd_pqhist(
    ctx: Environment,
    samples: int,
    bins: int,
    chan: list[int],
    trig: dict[int, "DTriggerConfigReq"],
    dpi: float,
    hold_after_trigger: bool,
    fmt: list[list[str]],
    write: str,
) -> bool:
    """[plugin] Static histogram plot for a given number of samples."""
    del hold_after_trigger
    return enable_plot_command(
        ctx,
        "q_hist",
        samples=samples,
        bins=bins,
        channels=chan,
        trig=trig,
        dpi=dpi,
        fmt=fmt,
        write=write,
    )
