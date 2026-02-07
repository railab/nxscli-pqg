"""Module containing animation1 plugin."""

from typing import TYPE_CHECKING, Any

from nxscli_pqg.animation_pqg import IPluginAnimation
from nxscli_pqg.plot_pqg import PlotDataAxesPqg, PluginAnimationCommonPqg

if TYPE_CHECKING:
    from nxscli.idata import PluginQueueData


###############################################################################
# Class: Animation1
###############################################################################


class LiveAnimation(PluginAnimationCommonPqg):
    """Infinity animation with x axis extension."""

    def __init__(
        self,
        plot_data: PlotDataAxesPqg,
        queue_data: "PluginQueueData",
        write: str,
        hold_after_trigger: bool = False,
        hold_post_samples: int = 0,
    ) -> None:
        """Initialize an animation1 handler.

        :param plot_data: axes handler
        :param queue_data: stream queue handler
        :param write: write path
        """
        PluginAnimationCommonPqg.__init__(
            self,
            plot_data,
            queue_data,
            write,
            hold_after_trigger=hold_after_trigger,
            hold_post_samples=hold_post_samples,
        )

        # Enable auto-range for X axis only (Y axis manually managed)
        plot_data.enable_auto_range(x=True, y=False)

        # Track Y-axis limits (start with small range)
        self._ymin = 0.0
        self._ymax = 1.0
        plot_data.set_ylim((self._ymin, self._ymax))

    def _animation_update(
        self,
        xdata: list[Any],
        ydata: list[Any],
        trigger_x: float | None = None,
    ) -> None:  # pragma: no cover
        """Update animation with dynamic scaling."""
        plot_data = self._plot_data

        # update sample data
        plot_data.xdata_extend(xdata)
        plot_data.ydata_extend(ydata)
        if trigger_x is not None or not self._hold_after_trigger:
            plot_data.set_trigger_marker(trigger_x)

        # update Y-axis limits (extend only, never shrink)
        self._update_ylim(ydata)

        # set new data on curves
        for i, curve in enumerate(plot_data.curves):
            curve.setData(plot_data.xdata[i], plot_data.ydata[i])
        if plot_data.trigger_x is not None:
            plot_data.trigger_line.setValue(plot_data.trigger_x)
            plot_data.trigger_line.show()
        else:
            plot_data.trigger_line.hide()

    def _update_ylim(self, ydata: list[Any]) -> None:  # pragma: no cover
        """Update Y-axis limits based on new data (extend only).

        :param ydata: new Y data
        """
        non_empty = [series for series in ydata if len(series) > 0]
        if not non_empty:
            return

        # find min/max in new data
        ymin_new = min(float(min(series)) for series in non_empty)
        ymax_new = max(float(max(series)) for series in non_empty)

        # extend range if needed (never shrink)
        updated = False
        if ymin_new < self._ymin:
            self._ymin = ymin_new
            updated = True
        if ymax_new > self._ymax:
            self._ymax = ymax_new
            updated = True

        # update plot limits if changed
        if updated:
            # add 5% padding
            padding = (self._ymax - self._ymin) * 0.05
            self._plot_data.set_ylim(
                (self._ymin - padding, self._ymax + padding)
            )


###############################################################################
# Class: PluginLive
###############################################################################


class PluginLive(IPluginAnimation):
    """Infinity animation with x axis extension."""

    def __init__(self) -> None:
        """Initialize an animation1 plugin."""
        IPluginAnimation.__init__(self)

    def _start(
        self,
        pdata: PlotDataAxesPqg,
        qdata: "PluginQueueData",
        kwargs: Any,
    ) -> PluginAnimationCommonPqg:
        """Start an animation1 plugin."""
        return LiveAnimation(
            pdata,
            qdata,
            kwargs["write"],
            hold_after_trigger=kwargs.get("hold_after_trigger", False),
            hold_post_samples=kwargs.get("hold_post_samples", 0),
        )
