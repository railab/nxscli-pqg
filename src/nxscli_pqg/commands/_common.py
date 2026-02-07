"""Private helpers for plot command dispatch."""

from typing import TYPE_CHECKING, Any

import click

if TYPE_CHECKING:
    from nxscli.cli.environment import Environment


def enable_plot_command(
    ctx: "Environment",
    plugin_name: str,
    *,
    samples: int | None = None,
    maxsamples: int | None = None,
    **kwargs: Any,
) -> bool:
    """Enable a plot plugin while keeping CLI side effects consistent."""
    assert ctx.phandler
    kwargs["nostop"] = False

    if samples == 0:  # pragma: no cover
        ctx.waitenter = True
        kwargs["nostop"] = ctx.waitenter

    if maxsamples == 0:  # pragma: no cover
        click.secho("ERROR: Missing argument MAXSAMPLES", err=True, fg="red")
        return False

    if samples is not None:
        kwargs["samples"] = samples

    if maxsamples is not None:
        kwargs["maxsamples"] = maxsamples

    ctx.phandler.enable(plugin_name, **kwargs)
    ctx.needchannels = True
    return True
