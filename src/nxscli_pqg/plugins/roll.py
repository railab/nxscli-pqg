"""Module containing animation2 plugin."""

from typing import TYPE_CHECKING, Any

from nxscli_pqg.animation_pqg import IPluginAnimation
from nxscli_pqg.plot_pqg import PlotDataAxesPqg, PluginAnimationCommonPqg

if TYPE_CHECKING:
    from nxscli.idata import PluginQueueData


###############################################################################
# Class: Animation2
###############################################################################


class RollAnimation(PluginAnimationCommonPqg):
    """Animation with x axis saturation (sliding window)."""

    def __init__(
        self,
        plot_data: PlotDataAxesPqg,
        queue_data: "PluginQueueData",
        write: str,
        hold_after_trigger: bool = False,
        hold_post_samples: int = 0,
        static_xticks: bool = True,
    ):
        """Initialize an animation2 handler.

        :param plot_data: axes handler
        :param queue_data: stream queue handler
        :param write: write path
        :param static_xticks: use static X axis ticks
        """
        PluginAnimationCommonPqg.__init__(
            self,
            plot_data,
            queue_data,
            write,
            hold_after_trigger=hold_after_trigger,
            hold_post_samples=hold_post_samples,
        )

        self._static_xticks = static_xticks

        # Disable auto-range for both axes (manually managed)
        plot_data.enable_auto_range(x=False, y=False)

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
        """Update animation with saturated X axis."""
        if self._static_xticks:
            self._animation_update_staticx(xdata, ydata, trigger_x)
        else:
            self._animation_update_dynamicx(xdata, ydata, trigger_x)

    def _animation_update_staticx(
        self,
        xdata: list[Any],
        ydata: list[Any],
        trigger_x: float | None = None,
    ) -> None:  # pragma: no cover
        """Update animation with static X ticks."""
        plot_data = self._plot_data

        # update sample with saturation
        plot_data.xdata_extend_max(xdata)
        plot_data.ydata_extend_max(ydata)

        # update Y-axis limits (extend only, never shrink)
        self._update_ylim(ydata)

        # use simple index for X axis (0 to N)
        for i, curve in enumerate(plot_data.curves):
            x = list(range(len(plot_data.ydata[i])))
            curve.setData(x, plot_data.ydata[i])
        if trigger_x is not None and plot_data.xdata[0]:
            rel_trigger_x = trigger_x - plot_data.xdata[0][0]
            if 0 <= rel_trigger_x < len(plot_data.ydata[0]):
                plot_data.set_trigger_marker(rel_trigger_x)
                plot_data.trigger_line.setValue(rel_trigger_x)
                plot_data.trigger_line.show()
            else:
                plot_data.set_trigger_marker(None)
                plot_data.trigger_line.hide()
        elif self._hold_after_trigger and plot_data.trigger_x is not None:
            plot_data.trigger_line.setValue(plot_data.trigger_x)
            plot_data.trigger_line.show()
        else:
            plot_data.set_trigger_marker(None)
            plot_data.trigger_line.hide()

    def _animation_update_dynamicx(
        self,
        xdata: list[Any],
        ydata: list[Any],
        trigger_x: float | None = None,
    ) -> None:  # pragma: no cover
        """Update animation with dynamic X ticks."""
        plot_data = self._plot_data

        if not xdata or not ydata:
            return

        # update sample with saturation
        plot_data.xdata_extend_max(xdata)
        plot_data.ydata_extend_max(ydata)
        if trigger_x is not None or not self._hold_after_trigger:
            plot_data.set_trigger_marker(trigger_x)

        # update Y-axis limits (extend only, never shrink)
        self._update_ylim(ydata)

        # use actual X data
        for i, curve in enumerate(plot_data.curves):
            curve.setData(plot_data.xdata[i], plot_data.ydata[i])

        # update X range to follow data
        if plot_data.xdata[0]:
            xmin = plot_data.xdata[0][0]
            xmax = plot_data.xdata[0][-1]
            plot_data.set_xlim((xmin, xmax))
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
# Class: PluginRoll
###############################################################################


class PluginRoll(IPluginAnimation):
    """Animation with x axis saturation."""

    def __init__(self) -> None:
        """Initialize an animation2 plugin."""
        IPluginAnimation.__init__(self)

    def _start(
        self,
        pdata: PlotDataAxesPqg,
        qdata: "PluginQueueData",
        kwargs: Any,
    ) -> PluginAnimationCommonPqg:
        """Start an animation2 plugin."""
        maxsamples = kwargs["maxsamples"]

        # configure the max number of samples
        pdata.samples_max = maxsamples
        pdata.set_xlim((0, maxsamples))

        # start animation
        return RollAnimation(
            pdata,
            qdata,
            kwargs["write"],
            hold_after_trigger=kwargs.get("hold_after_trigger", False),
            hold_post_samples=kwargs.get("hold_post_samples", 0),
            static_xticks=True,
        )
