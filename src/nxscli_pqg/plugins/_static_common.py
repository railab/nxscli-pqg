"""Shared static-plot helpers for pqg plugins."""

from typing import TYPE_CHECKING, Any

import numpy as np
from nxscli.iplugin import IPluginPlotStatic
from nxscli.pluginthr import PluginThread, StreamBlocks

from nxscli_pqg.plot_pqg import PluginPlotPqg, build_plot_surface

if TYPE_CHECKING:
    from nxscli.idata import PluginQueueData


class _PluginStaticBase(PluginThread, IPluginPlotStatic):
    """Common static-plot startup and queue handling for pqg plugins."""

    def __init__(self) -> None:
        IPluginPlotStatic.__init__(self)
        PluginThread.__init__(self)
        self._plot: "PluginPlotPqg"
        self._write: str = ""

    def get_plot_handler(self) -> "PluginPlotPqg | None":
        """Return the pyqtgraph plot handler or None before start."""
        return getattr(self, "_plot", None)

    def _init(self) -> None:  # pragma: no cover
        assert self._phandler

    def _handle_blocks(
        self, data: StreamBlocks, pdata: "PluginQueueData", j: int
    ) -> None:
        ydata: list[list[Any]] = [[] for _ in range(pdata.vdim)]
        for block in data:
            block_data = block.data
            assert isinstance(block_data, np.ndarray)
            if int(block_data.shape[0]) == 0:  # pragma: no cover
                continue
            for i in range(pdata.vdim):
                ydata[i].extend(block_data[:, i])

        self._plot.plist[j].ydata_extend(ydata)
        event_getter = getattr(pdata, "pop_trigger_event", None)
        event = event_getter() if callable(event_getter) else None
        if event is not None:
            self._plot.plist[j].set_trigger_marker(
                self._datalen[j] + event.sample_index
            )
        self._datalen[j] = len(self._plot.plist[j].ydata[0])

    def _start_plot(self, kwargs: dict[str, Any]) -> bool:
        assert self._phandler

        self._samples = kwargs["samples"]
        self._write = str(kwargs["write"]) if kwargs["write"] else ""
        self._nostop = kwargs["nostop"]
        self._plot = build_plot_surface(self._phandler, kwargs)

        if not self._plot.qdlist or not self._plot.plist:  # pragma: no cover
            return False
        return True

    def _set_initial_xlim(self) -> None:
        if not self._samples:
            return
        for pdata in self._plot.plist:
            pdata.set_xlim((0, self._samples))

    def _save_plot(self) -> None:
        if self._write:  # pragma: no cover
            self._plot.savefig(self._write)
