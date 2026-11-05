"""
modules/retro_monitor/demo.py

Standalone proof-of-concept: opens RetroMonitorFrame in a Tk window and
places a live interactive mock terminal inside the screen area.

The mock terminal accepts typed commands and echoes responses — no Docker,
no pipeline, no external dependencies.  It exists solely to prove that an
arbitrary interactive Tkinter widget can live inside the monitor screen area.

Run from the project root:

    python modules/retro_monitor/demo.py

Options:
    --calibrate   Overlay a red rectangle showing the current screen_rect
                  coordinates so you can tune screen_rect.json visually.
    --bezel PATH  Use a specific bezel PNG instead of assets/monitor_bezel.png.
"""

from __future__ import annotations

import argparse
import sys
import tkinter as tk
from pathlib import Path
from typing import Optional

_MODULE_ROOT = Path(__file__).resolve().parent
if str(_MODULE_ROOT.parent.parent) not in sys.path:
    sys.path.insert(0, str(_MODULE_ROOT.parent.parent))

from modules.retro_monitor.frame import RetroMonitorFrame

# ------------------------------------------------------------------
# Screen colour constants (intentionally independent of KleinBOTTLE)
# ------------------------------------------------------------------
_BG        = "#0a0f0a"   # very dark green-black (phosphor screen)
_FG        = "#33ff33"   # classic green phosphor
_PROMPT    = "#00cc22"
_CURSOR_BG = "#33ff33"
_FONT      = ("Courier", 9)
_FONT_B    = ("Courier", 9, "bold")


# ------------------------------------------------------------------
# MockTerminal — a self-contained interactive text widget
# ------------------------------------------------------------------

class MockTerminal(tk.Frame):
    """
    A minimal read-eval-print widget that lives inside the monitor screen.

    Commands are handled locally — this widget is intentionally independent
    of any real shell or backend. Its job is to prove that the RetroMonitorFrame
    container works with a live, interactive child widget.

    Once the monitor module is integrated into KleinBOTTLE, the game will
    inject its own Frame (backed by ComputerBackend) in place of this stub.
    """

    _HELP = (
        "Mock terminal — commands run locally, no Docker\n"
        "  help          this message\n"
        "  echo <text>   print text\n"
        "  clear         clear screen\n"
        "  about         module info\n"
        "  date          show current date/time\n"
        "  quit / exit   close the window\n"
    )

    def __init__(self, parent: tk.Misc, **kw: object) -> None:
        super().__init__(parent, bg=_BG, bd=0, highlightthickness=0, **kw)  # type: ignore[arg-type]

        self._output = tk.Text(
            self,
            bg=_BG, fg=_FG,
            insertbackground=_CURSOR_BG,
            font=_FONT,
            wrap="word",
            state="disabled",
            bd=0, highlightthickness=0,
            relief="flat",
            padx=6, pady=6,
        )
        self._output.pack(fill="both", expand=True)

        bar = tk.Frame(self, bg=_BG)
        bar.pack(fill="x", padx=6, pady=(0, 6))

        tk.Label(bar, text="$ ", bg=_BG, fg=_PROMPT, font=_FONT_B).pack(side="left")

        self._entry = tk.Entry(
            bar,
            bg=_BG, fg=_FG,
            insertbackground=_CURSOR_BG,
            font=_FONT,
            bd=0, highlightthickness=1,
            highlightbackground="#1a3a1a",
            highlightcolor=_FG,
            relief="flat",
        )
        self._entry.pack(side="left", fill="x", expand=True)
        self._entry.bind("<Return>", self._on_enter)
        self._entry.focus_set()

        self._print("KleinOS Mock Terminal v0.1\n")
        self._print("Type  help  for available commands.\n\n")
        self._print("$ ")

    def _print(self, text: str, tag: Optional[str] = None) -> None:
        self._output.configure(state="normal")
        if tag:
            self._output.insert("end", text, tag)
        else:
            self._output.insert("end", text)
        self._output.see("end")
        self._output.configure(state="disabled")

    def _on_enter(self, _event: Optional[tk.Event] = None) -> None:
        cmd = self._entry.get().strip()
        self._entry.delete(0, "end")
        self._print(cmd + "\n")
        self._run(cmd)
        self._print("\n$ ")

    def _run(self, cmd: str) -> None:
        import datetime

        if not cmd:
            return
        verb, _, rest = cmd.partition(" ")
        verb = verb.lower()

        if verb in ("help", "?"):
            self._print(self._HELP)
        elif verb == "echo":
            self._print((rest or "") + "\n")
        elif verb == "clear":
            self._output.configure(state="normal")
            self._output.delete("1.0", "end")
            self._output.configure(state="disabled")
        elif verb == "about":
            self._print(
                "RetroMonitorFrame — image-generation-pipeline\n"
                "modules/retro_monitor/frame.py\n"
                "A generic Tk container for retro monitor visuals.\n"
            )
        elif verb == "date":
            self._print(datetime.datetime.now().strftime("%A %d %B %Y  %H:%M:%S\n"))
        elif verb in ("quit", "exit"):
            self.winfo_toplevel().destroy()
        else:
            self._print(f"{verb}: command not found\n")


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="RetroMonitorFrame demo")
    parser.add_argument(
        "--calibrate", action="store_true",
        help="Overlay red rect showing current screen_rect.json coordinates",
    )
    parser.add_argument(
        "--bezel", type=Path, default=None,
        help="Path to a bezel PNG (default: assets/monitor_bezel.png)",
    )
    args = parser.parse_args()

    root = tk.Tk()
    root.title("RetroMonitorFrame — demo")
    root.resizable(False, False)
    root.configure(bg="#111")

    monitor = RetroMonitorFrame(
        root,
        bezel_path=args.bezel,
    )
    monitor.pack(padx=16, pady=16)

    # Place the mock terminal inside the screen
    terminal = MockTerminal(monitor.screen)
    terminal.pack(fill="both", expand=True)

    if args.calibrate:
        _draw_calibration(monitor)

    root.mainloop()


def _draw_calibration(monitor: RetroMonitorFrame) -> None:
    """Draw a bright red border around the screen rect for visual calibration."""
    import json
    rect_path = _MODULE_ROOT / "assets" / "screen_rect.json"
    if not rect_path.exists():
        return
    try:
        d = json.loads(rect_path.read_text())
        x, y, w, h = int(d["x"]), int(d["y"]), int(d["width"]), int(d["height"])
    except (ValueError, KeyError, OSError):
        return
    monitor._canvas.create_rectangle(
        x - 2, y - 2, x + w + 2, y + h + 2,
        outline="#ff0000", width=3, dash=(6, 4),
    )
    monitor._canvas.create_text(
        x + 4, y + 4, anchor="nw",
        text=f"({x}, {y})  {w}×{h}",
        fill="#ff4444", font=("Courier", 8),
    )


if __name__ == "__main__":
    main()
