# retro_monitor — Pipeline Module

A generic Tkinter container that wraps any child widget in a retro CRT
monitor illustration.  Zero runtime dependencies on KleinBOTTLE, ComfyUI,
or the image-generation pipeline.

## Concept

```
┌────────────────────────────────────────────────────┐
│          [monitor bezel PNG or fallback]            │
│   ┌──────────────────────────────────────────┐     │
│   │                                          │     │
│   │     monitor.screen  (tk.Frame)           │     │
│   │     ← put any Tkinter widget here        │     │
│   │                                          │     │
│   └──────────────────────────────────────────┘     │
└────────────────────────────────────────────────────┘
```

The screen rectangle coordinates come from `assets/screen_rect.json`.
Tune them to match your bezel image — no code changes needed.

## Files

```
modules/retro_monitor/
├── frame.py            RetroMonitorFrame(tk.Frame) — the container
├── generate_bezel.py   One-shot asset-generation script (needs ComfyUI)
├── demo.py             Standalone proof-of-concept
├── assets/
│   ├── monitor_bezel.png   generated bezel PNG (commit after generation)
│   └── screen_rect.json    screen region coordinates
└── README.md
```

## Requirements

| Dependency | How to get |
|---|---|
| Python 3.8+ | Shipped with ComfyUI / Stability Matrix |
| `tkinter` | Standard library (always present) |
| `Pillow` | `pip install pillow` — required to load the PNG bezel |

Without Pillow (or before `generate_bezel.py` has been run) the frame
renders a programmatic CRT shape instead, so the demo works immediately.

## Quick start

```bash
# Run the demo — works right away with the built-in fallback bezel
python modules/retro_monitor/demo.py

# Generate the PNG bezel (requires ComfyUI running)
python modules/retro_monitor/generate_bezel.py

# Run the demo with the generated PNG
python modules/retro_monitor/demo.py

# Overlay calibration guides to tune screen_rect.json
python modules/retro_monitor/demo.py --calibrate
```

## Embedding your own widget

```python
import tkinter as tk
from modules.retro_monitor import RetroMonitorFrame

root = tk.Tk()
monitor = RetroMonitorFrame(root)
monitor.pack()

# Place anything you like inside the screen area
your_widget = YourWidget(monitor.screen)
your_widget.pack(fill="both", expand=True)

root.mainloop()
```

`monitor.screen` is a plain `tk.Frame` at the exact coordinates defined in
`screen_rect.json`. Pack, grid, or place your content widget inside it.

## API

### `RetroMonitorFrame(parent, *, asset_dir, bezel_path, rect_path, fallback_w, fallback_h)`

| Parameter | Default | Description |
|---|---|---|
| `asset_dir` | `assets/` next to `frame.py` | Directory containing the PNG and JSON |
| `bezel_path` | `asset_dir/monitor_bezel.png` | Override path for the bezel PNG |
| `rect_path`  | `asset_dir/screen_rect.json` | Override path for the screen rect |
| `fallback_w` | `640` | Canvas width when no PNG is available |
| `fallback_h` | `480` | Canvas height when no PNG is available |

### `monitor.screen`

A `tk.Frame` positioned over the monitor's screen area. Use it as the
parent for any content widget.

## Generating the bezel PNG

```bash
python modules/retro_monitor/generate_bezel.py [--style default] [--out assets/monitor_bezel.png]
```

The script submits a CRT monitor prompt to ComfyUI and saves the result.
Commit `assets/monitor_bezel.png` once you're happy with it.

After generation, run with `--calibrate` to check the screen rectangle:

```bash
python modules/retro_monitor/demo.py --calibrate
```

If the red overlay doesn't match the screen area, edit `screen_rect.json`:

```json
{
  "x": 108,
  "y": 82,
  "width": 424,
  "height": 316
}
```

Reload the demo to see the change — no regeneration needed.

## Integrating KleinBOTTLE's terminal

The `ComputerWindow` in KleinBOTTLE is currently a `tk.Toplevel`. The
integration path (not done here) is:

1. Extract the terminal tab's content into a `MonitorTerminalPane(tk.Frame)`
   backed by the existing `ComputerBackend`.
2. Pass a shared `ComputerBackend` instance into it.
3. Instantiate `RetroMonitorFrame` as the outer window.
4. Pack `MonitorTerminalPane(monitor.screen)` inside `monitor.screen`.

The `RetroMonitorFrame` doesn't care what's inside `screen` — it only
manages the visual chrome.
