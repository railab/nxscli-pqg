"""The pyqtgraph plot specific command."""

import click
from nxscli.cli.environment import Environment, pass_environment

from nxscli_pqg.plot_pqg import PqgManager

###############################################################################
# Command: cmd_pqg
###############################################################################


@click.command(name="pqg")
@click.option(
    "--background",
    default="w",
    type=str,
    help="Background color (default: w for white)",
)
@click.option(
    "--foreground",
    default="k",
    type=str,
    help="Foreground color (default: k for black)",
)
@click.option(
    "--antialias/--no-antialias",
    default=False,
    help="Enable antialiasing (default: disabled for performance)",
)
@pass_environment
def cmd_pqg(
    ctx: Environment, background: str, foreground: str, antialias: bool
) -> bool:
    """[config] PyQtGraph configuration."""  # noqa: D301
    PqgManager.configure(
        background=background, foreground=foreground, antialias=antialias
    )
    return True


# default configuration
PqgManager.configure(background="w", foreground="k", antialias=False)
