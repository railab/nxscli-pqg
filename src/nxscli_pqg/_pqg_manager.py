"""Private pyqtgraph manager helpers."""

import sys

import pyqtgraph as pg  # type: ignore
from nxscli.logger import logger
from PyQt6.QtWidgets import QApplication, QMainWindow


class PqgManager:
    """PyQtGraph global manager."""

    _app: QApplication | None = None
    _windows: list[QMainWindow] = []

    @classmethod
    def get_app(cls) -> QApplication:
        """Get or create QApplication instance."""
        if cls._app is None:
            cls._app = QApplication.instance()  # type: ignore
            if cls._app is None:  # pragma: no branch
                cls._app = QApplication(sys.argv)
        return cls._app

    @classmethod
    def register_window(cls, window: QMainWindow) -> None:
        """Register a tracked Qt window."""
        cls._windows.append(window)

    @classmethod
    def unregister_window(cls, window: QMainWindow) -> None:
        """Remove a tracked Qt window."""
        if window in cls._windows:
            cls._windows.remove(window)

    @classmethod
    def fig_is_open(cls) -> bool:  # pragma: no cover
        """Return whether any tracked window is visible."""
        cls._windows = [w for w in cls._windows if w.isVisible()]
        return len(cls._windows) > 0

    @classmethod
    def process_events(cls) -> None:  # pragma: no cover
        """Process pending Qt events."""
        if cls._app:
            cls._app.processEvents()

    @classmethod
    def show(cls, block: bool = True) -> None:  # pragma: no cover
        """Show tracked windows and optionally block in the event loop."""
        if cls._app:
            if block:
                cls._app.exec()
            else:
                cls._app.processEvents()

    @staticmethod
    def configure(
        background: str = "w",
        foreground: str = "k",
        antialias: bool = False,
    ) -> None:
        """Configure global pyqtgraph appearance."""
        logger.info(
            "pqg config: bg=%s, fg=%s, antialias=%s",
            background,
            foreground,
            antialias,
        )
        pg.setConfigOption("background", background)
        pg.setConfigOption("foreground", foreground)
        pg.setConfigOption("antialias", antialias)
