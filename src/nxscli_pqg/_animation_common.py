"""Private pyqtgraph animation queue helpers."""

from typing import TYPE_CHECKING, Any

import numpy as np
from nxslib.nxscope import DNxscopeStreamBlock

from nxscli_pqg._plot_constants import ANIMATION_FRAME_DRAIN_LIMIT

if TYPE_CHECKING:
    from nxscli.idata import PluginQueueData


def init_xy_buffers(vdim: int) -> tuple[list[list[Any]], list[list[Any]]]:
    """Create empty X/Y buffers for one animation frame."""
    xdata: list[list[Any]] = []
    ydata: list[list[Any]] = []
    for _ in range(vdim):
        xdata.append([])
        ydata.append([])
    return xdata, ydata


def append_block_chunks(
    block: DNxscopeStreamBlock,
    *,
    qdim: int,
    count: int,
    x_chunks: list[np.ndarray[Any, Any]],
    y_chunks: list[list[np.ndarray[Any, Any]]],
) -> int:
    """Append one queue block to frame chunks and return the updated count."""
    if not isinstance(block, DNxscopeStreamBlock):
        raise RuntimeError(
            "plot animation requires DNxscopeStreamBlock payload"
        )

    nsamples = int(block.data.shape[0])
    if nsamples == 0:
        return count

    xr = np.arange(count, count + nsamples)
    x_chunks.append(xr)
    for i in range(qdim):
        y_chunks[i].append(block.data[:, i])
    return count + nsamples


def flush_chunks(
    *,
    vdim: int,
    x_chunks: list[np.ndarray[Any, Any]],
    y_chunks: list[list[np.ndarray[Any, Any]]],
    xdata: list[list[Any]],
    ydata: list[list[Any]],
) -> tuple[list[list[Any]], list[list[Any]]]:
    """Flush accumulated chunk arrays into list buffers."""
    if x_chunks:
        xcat = np.concatenate(x_chunks)
        for i in range(vdim):
            xdata[i].extend(xcat)

    for i in range(vdim):
        if y_chunks[i]:
            ydata[i].extend(np.concatenate(y_chunks[i]))

    return xdata, ydata


def fetch_animation_data(
    qdata: "PluginQueueData",
    *,
    count: int,
    limit: int = ANIMATION_FRAME_DRAIN_LIMIT,
    stop_on_trigger: bool = False,
) -> tuple[
    list[np.ndarray[Any, Any]],
    list[np.ndarray[Any, Any]],
    int,
    float | None,
]:
    """Drain one animation frame from the queue and return updated counters."""
    x_chunks: list[np.ndarray[Any, Any]] = []
    y_chunks: list[list[np.ndarray[Any, Any]]] = [
        [] for _ in range(qdata.vdim)
    ]

    next_count = count
    trigger_x: float | None = None
    for _ in range(limit):
        blocks = qdata.queue_get(block=False)
        if not blocks:
            break
        if not isinstance(blocks, list):
            raise RuntimeError("plot animation queue payload must be list")
        event_getter = getattr(qdata, "pop_trigger_event", None)
        event = event_getter() if callable(event_getter) else None
        batch_start = next_count
        if event is not None and trigger_x is None:
            trigger_x = batch_start + event.sample_index
        had_samples = False
        for block in blocks:
            prev_count = next_count
            next_count = append_block_chunks(
                block,
                qdim=qdata.vdim,
                count=next_count,
                x_chunks=x_chunks,
                y_chunks=y_chunks,
            )
            had_samples = had_samples or next_count > prev_count
        if stop_on_trigger and event is not None and had_samples:
            break

    xcat = (
        np.concatenate(x_chunks)
        if x_chunks
        else np.empty((0,), dtype=np.int64)
    )
    xdata = [xcat for _ in range(qdata.vdim)]
    ydata = [
        (
            np.concatenate(chunks)
            if chunks
            else np.empty((0,), dtype=np.float64)
        )
        for chunks in y_chunks
    ]
    return xdata, ydata, next_count, trigger_x
