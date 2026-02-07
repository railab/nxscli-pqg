"""Dedicated FFT plot plugin."""

from nxscli_pqg.plugins._typed_static import PluginTypedStatic


class PluginFft(PluginTypedStatic):
    """Render static FFT view."""

    plot_type = "fft"
