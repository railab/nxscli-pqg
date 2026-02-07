"""Private public-API types for pqg plots."""

from dataclasses import dataclass
from enum import Enum


class EPlotMode(Enum):
    """Available plot display modes."""

    DETACHED = "detached"
    ATTACHED = "attached"

    @classmethod
    def from_text(cls, value: str) -> "EPlotMode":
        """Parse mode string with safe fallback."""
        for mode in cls:
            if mode.value == value:
                return mode
        return cls.DETACHED


@dataclass(frozen=True)
class PlotVectorState:
    """Per-vector visibility state."""

    channel: int
    vector: int
    visible: bool
