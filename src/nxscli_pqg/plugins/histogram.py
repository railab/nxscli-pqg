"""Dedicated histogram plot plugin."""

from nxscli_pqg.plugins._typed_static import PluginTypedStatic


class PluginHistogram(PluginTypedStatic):
    """Render static histogram view."""

    plot_type = "histogram"
