"""Pytest configuration for nxscli-pqg tests."""

import pytest


@pytest.fixture(autouse=True)
def cleanup_qt():
    """Cleanup Qt resources after each test."""
    yield
    # Process any pending Qt events
    try:
        from nxscli_pqg.plot_pqg import PqgManager

        if PqgManager._app:
            PqgManager._app.processEvents()
        # Close any remaining windows
        for window in list(PqgManager._windows):
            try:  # pragma: no cover
                window.close()  # pragma: no cover
            except RuntimeError:  # pragma: no cover
                pass
        PqgManager._windows.clear()  # pragma: no cover
    except Exception:  # pragma: no cover
        pass
