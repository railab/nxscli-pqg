"""Module containing the Click types for nxscli-pqg."""  # noqa: A005

from typing import Any

import click
from nxscli.cli.types import (
    Channels,
    StringList2,
    Trigger,
    channels_option_help,
    trigger_option_help,
)

from nxscli_pqg._plot_format import parse_format_string

###############################################################################
# Class: FormatStringList
###############################################################################


class FormatStringList(StringList2):
    """Parse and validate format string list argument."""

    def convert(self, value: Any, param: Any, ctx: Any) -> list[list[str]]:
        """Convert and validate format string argument."""
        # Parse using parent class
        result = super().convert(value, param, ctx)

        # Validate each format string
        if result:
            for i, channel_fmts in enumerate(result):
                for j, fmt in enumerate(channel_fmts):
                    if fmt:  # Skip empty strings
                        try:
                            parse_format_string(fmt)
                        except ValueError as e:
                            self.fail(
                                f"\n\n{str(e)}\n\n"
                                f"Error in channel {i}, "
                                f"vector {j}: '{fmt}'",
                                param,
                                ctx,
                            )

        return result


###############################################################################
# Globals: stirngs
###############################################################################


fmt_option_help = """Plugin specific pyqtgraph format string configuration.
                     Channels separated by a semicolon (;),
                     vectors separated by question marks (?).
                     Format: [color][linestyle][marker] (matplotlib-style)
                     Colors: 'r' (red), 'g' (green), 'b' (blue),
                     'c' (cyan), 'm' (magenta), 'y' (yellow), 'w' (white),
                     'k' (black).
                     Line styles: '-' (solid), '--' (dashed), '-.' (dash-dot),
                     ':' (dotted).
                     Markers: 'o' (circle), 's' (square), '+' (plus),
                     'x' (cross), 'd' (diamond), 't' (triangle),
                     'star' (star).
                     Examples: 'r-?g--?b:' (colors + line styles),
                     'ro?gs?bx' (colors + markers),
                     'r-o?g--s?b:+' (colors + line styles + markers).
                     Default: cycles through r, g, b, c, m, y, w (solid lines).
                      """  # noqa: D301


###############################################################################
# Decorator: plot_options
###############################################################################


# common plot options
_plot_options = (
    click.option(
        "--chan",
        default=None,
        type=Channels(),
        help=channels_option_help,
    ),
    click.option(
        "--trig",
        default=None,
        type=Trigger(),
        help=trigger_option_help,
    ),
    click.option("--dpi", type=int, default=100),
    click.option(
        "--hold-after-trigger",
        is_flag=True,
        default=False,
        help="Stop live plot updates after the first trigger event.",
    ),
    click.option(
        "--fmt",
        default="",
        type=FormatStringList(ch1="?"),
        help=fmt_option_help,
    ),
    click.option("--write", type=click.Path(resolve_path=False), default=""),
)


def plot_options(fn: Any) -> Any:
    """Decorate command with common plot options decorator."""
    for decorator in reversed(_plot_options):
        fn = decorator(fn)
    return fn
