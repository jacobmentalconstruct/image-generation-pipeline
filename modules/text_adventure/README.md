# text_adventure — Pipeline Module

King's Quest-style item viewer for text adventure games.

This module pulls images from the ComfyUI pipeline and displays them in a
Tkinter window that mimics the mixed text/image presentation of Sierra's
early adventure games (KQ1–KQ5 era): bordered image panel on top, item name
in a blue title bar, and scrollable flavour text below.

## Requirements

| Dependency | How to get |
|---|---|
| Python 3.8+ | Shipped with ComfyUI / Stability Matrix |
| `tkinter` | Standard library (always present) |
| `Pillow` | `pip install pillow` |
| ComfyUI running | Stability Matrix → Launch |

## Quick start

```python
import sys
sys.path.insert(0, r"C:\Jacob\Apps & Tools\image-generation-pipeline")
from modules.text_adventure import show_item

show_item(
    name="Ancient Amulet",
    description="A tarnished silver amulet inscribed with strange runes. "
                "It hums faintly when you hold it.",
    style="default",   # any style profile in styles/
)
```

The window **blocks** until the player presses **Enter**, **Escape**, or
closes it — the same feel as KQ's examine-item screens.

## Demo

```bash
# Generate an image on the fly (ComfyUI must be running)
python modules/text_adventure/demo.py --item amulet

# Skip generation — use an existing image
python modules/text_adventure/demo.py --item key --image output/some_image.png

# Use a different style profile
python modules/text_adventure/demo.py --item scroll --style kleinbottle
```

Available demo items: `amulet`, `key`, `scroll`, `lantern`.

## API

### `show_item(name, description, style, image_path, out_dir, timeout)`

Convenience wrapper — builds an `ItemViewer` and calls `.show()`.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `name` | `str` | required | Item name shown in title bar and description header |
| `description` | `str` | required | Flavour text in the lower panel |
| `style` | `str` | `"default"` | Style profile from `styles/` |
| `image_path` | `Path \| None` | `None` | Pre-generated image; skips generation when provided |
| `out_dir` | `Path \| None` | `output/text_adventure/` | Where generated images are saved |
| `timeout` | `float` | `300.0` | Max seconds to wait for ComfyUI |

### `ItemViewer`

The underlying class if you need more control (e.g. subclassing or threading):

```python
from modules.text_adventure import ItemViewer

viewer = ItemViewer(name="Iron Key", description="Pitted with rust.")
viewer.show()  # blocks
```

### `generate_item_image(name, description, style, out_dir, timeout) → Path`

Generate only — no window. Returns the saved image path. Useful for
pre-generating assets during a loading screen.

```python
from modules.text_adventure.item_viewer import generate_item_image

path = generate_item_image("Brass Lantern", "Old but still burning.")
print(path)  # e.g. output/text_adventure/ComfyUI_00042_.png
```

## How the prompt is constructed

The module builds a ComfyUI prompt automatically:

```
{name}, {description}, inventory item, isolated on black, detailed illustration
```

This is then passed through the style profile's prefix/suffix and LoRA
settings — so changing `--style` changes the entire visual language of
every item in your game.

## Threading

Generation runs in a background thread; the window stays responsive and
shows an animated "Generating…" indicator. If your text adventure loop
needs to stay live while the window is open, call `show_item` from a
dedicated thread:

```python
import threading
t = threading.Thread(target=show_item, kwargs={"name": "...", "description": "..."})
t.start()
# your game loop continues here
t.join()  # wait for player to dismiss
```

## Visual layout

```
┌──────────────────────────────────────────────┐
│  ANCIENT AMULET                              │  ← title bar (EGA blue)
├──────────────────────────────────────────────┤
│                                              │
│            [generated image]                 │  ← image panel (320 px tall)
│                                              │
├──────────────────────────────────────────────┤
│ Ancient Amulet                               │  ← item name (gold)
│                                              │
│ A tarnished silver amulet inscribed with     │  ← flavour text (scrollable)
│ strange runes…                               │
│                                              │
│ [ Press ENTER or close window to continue ]  │
└──────────────────────────────────────────────┘
```

## Extending

This module lives in `modules/text_adventure/`. Other pipeline-integrated
subsystems for other apps follow the same pattern under `modules/<app_type>/`.
To add a new widget (e.g. a scene background viewer or NPC portrait):

1. Create `modules/text_adventure/<new_widget>.py`
2. Export it from `modules/text_adventure/__init__.py`
3. Add a row to the modules table in `modules/text_adventure/README.md`
