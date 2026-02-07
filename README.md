# Nxscli-pqg
![master workflow](https://github.com/railab/nxscli-pqg/actions/workflows/master.yml/badge.svg)

PyQtGraph extension to Nxscli.

## Features

* Plotting with [PyQtGraph](https://github.com/pyqtgraph/pyqtgraph/),
  * static time-series capture (`q_snap`)
  * animation plots (`q_live`, `q_roll`)
  * static and streaming FFT (`q_fft`, `q_fft_live`)
  * static and streaming histogram (`q_hist`, `q_hist_live`)
  * static and streaming XY (`q_xy`, `q_xy_live`)
  * static and streaming polar (`q_polar`, `q_polar_live`)
  * Matplotlib-style format strings (colors, line styles, markers)
  * PyQtGraph style configuration (`pqg`)

## Installation

Nxscli-pqg can be installed by running `pip install nxscli-pqg`.

To install latest development version, use:

`pip install git+https://github.com/railab/nxscli-pqg.git`
