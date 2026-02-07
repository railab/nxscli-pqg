=====
Usage
=====

Configuration commands
======================

* ``pqg`` - PyQtGraph configuration.

  Optional, at default:

  - background = "w" (white)
  - foreground = "k" (black)
  - antialias = False

Format strings
==============

The ``--fmt`` option supports matplotlib-style format strings to customize plot
appearance:

* **Format**: ``[color][linestyle][marker]``
* **Colors**: ``r`` (red), ``g`` (green), ``b`` (blue), ``c`` (cyan),
  ``m`` (magenta), ``y`` (yellow), ``w`` (white), ``k`` (black)
* **Line styles**: ``-`` (solid), ``--`` (dashed), ``-.`` (dash-dot),
  ``:`` (dotted)
* **Markers**: ``o`` (circle), ``s`` (square), ``+`` (plus), ``x`` (cross),
  ``d`` (diamond), ``t`` (triangle), ``star`` (star)

Examples:

* ``r-`` - Red solid line
* ``b--`` - Blue dashed line
* ``go`` - Green circles (markers only)
* ``k-.+`` - Black dash-dot line with plus markers

Plugin commands
===============

Plugins supported so far:

* ``q_live`` - infinite animation plot (no X-axis limits)
* ``q_roll`` - animation plot with X-axis saturation
* ``q_snap`` - static plot (capture data and plot)
* ``q_fft`` - static FFT plot
* ``q_fft_live`` - streaming FFT plot
* ``q_hist`` - static histogram plot
* ``q_hist_live`` - streaming histogram plot
* ``q_xy`` - static XY plot
* ``q_xy_live`` - streaming XY plot
* ``q_polar`` - static polar plot
* ``q_polar_live`` - streaming polar plot

For more information, use the plugin's ``--help`` option.

CLI Test Commands
=================

All commands below were validated against ``dummy`` interface.

Important syntax rule for chained commands:

* plugin options must be placed before positional args
  (for example ``q_fft_live --hop 128 512``, not
  ``q_fft_live 512 --hop 128``).

Static plots
------------

.. code-block:: bash

   QT_QPA_PLATFORM=offscreen python -m nxscli dummy chan 0 q_snap 1200
   QT_QPA_PLATFORM=offscreen python -m nxscli dummy chan 9 q_fft 2048
   QT_QPA_PLATFORM=offscreen python -m nxscli dummy chan 0 q_hist --bins 64 2000
   QT_QPA_PLATFORM=offscreen python -m nxscli dummy chan 0,2 q_xy 1500
   QT_QPA_PLATFORM=offscreen python -m nxscli dummy chan 15 q_xy 1500
   QT_QPA_PLATFORM=offscreen python -m nxscli dummy chan 0,2 q_polar 1500
   QT_QPA_PLATFORM=offscreen python -m nxscli dummy chan 16 q_polar 1500

Streaming plots
---------------

.. code-block:: bash

   QT_QPA_PLATFORM=offscreen python -m nxscli dummy chan 0 q_live
   QT_QPA_PLATFORM=offscreen python -m nxscli dummy chan 0 q_roll 512
   QT_QPA_PLATFORM=offscreen python -m nxscli dummy chan 9 q_fft_live --hop 64 256
   QT_QPA_PLATFORM=offscreen python -m nxscli dummy chan 0 q_hist_live --hop 64 --bins 32 256
   QT_QPA_PLATFORM=offscreen python -m nxscli dummy chan 0,2 q_xy_live --hop 64 256
   QT_QPA_PLATFORM=offscreen python -m nxscli dummy chan 15 q_xy_live --hop 64 256
   QT_QPA_PLATFORM=offscreen python -m nxscli dummy chan 0,2 q_polar_live --hop 64 256
   QT_QPA_PLATFORM=offscreen python -m nxscli dummy chan 16 q_polar_live --hop 64 256

For automated smoke checks in CI/shell, you can use timeout:

.. code-block:: bash

   QT_QPA_PLATFORM=offscreen timeout 8 python -m nxscli dummy chan 0 q_live
   QT_QPA_PLATFORM=offscreen timeout 8 python -m nxscli dummy chan 0 q_roll 512
   QT_QPA_PLATFORM=offscreen timeout 8 python -m nxscli dummy chan 9 q_fft_live --hop 64 256
   QT_QPA_PLATFORM=offscreen timeout 8 python -m nxscli dummy chan 0 q_hist_live --hop 64 --bins 32 256
   QT_QPA_PLATFORM=offscreen timeout 8 python -m nxscli dummy chan 0,2 q_xy_live --hop 64 256
   QT_QPA_PLATFORM=offscreen timeout 8 python -m nxscli dummy chan 15 q_xy_live --hop 64 256
   QT_QPA_PLATFORM=offscreen timeout 8 python -m nxscli dummy chan 0,2 q_polar_live --hop 64 256
   QT_QPA_PLATFORM=offscreen timeout 8 python -m nxscli dummy chan 16 q_polar_live --hop 64 256

PyQtGraph config command
------------------------

.. code-block:: bash

   QT_QPA_PLATFORM=offscreen python -m nxscli dummy pqg --background k --foreground w chan 0 q_snap 300

Keyboard shortcuts
==================

When a plot window is open, the following keyboard shortcuts are available:

* ``f`` or ``F`` - Toggle fullscreen mode
* ``q`` or ``Q`` - Close the plot window
* ``Escape`` - Close the plot window
