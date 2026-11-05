"""
modules/text_adventure/demo.py

Proof-of-concept: shows the item viewer for a handful of classic adventure
game items.  Run with ComfyUI active.

    python modules/text_adventure/demo.py
    python modules/text_adventure/demo.py --item amulet
    python modules/text_adventure/demo.py --style kleinbottle
"""

import argparse
import sys
from pathlib import Path

# Allow running directly from project root or from inside the module dir
_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from modules.text_adventure import show_item

DEMO_ITEMS = {
    "amulet": {
        "name": "Ancient Amulet",
        "description": (
            "A tarnished silver amulet inscribed with strange runes. "
            "It hums faintly when you hold it close to your ear, as if "
            "whispering secrets from another age."
        ),
    },
    "key": {
        "name": "Iron Skeleton Key",
        "description": (
            "An old iron key, pitted with rust but still sturdy. "
            "Three notches have been filed into the blade. "
            "Whatever lock it opens must be very old indeed."
        ),
    },
    "scroll": {
        "name": "Sealed Scroll",
        "description": (
            "A rolled parchment sealed with dark wax bearing a crest "
            "you do not recognise. The edges are scorched, as though "
            "it narrowly escaped a fire."
        ),
    },
    "lantern": {
        "name": "Brass Lantern",
        "description": (
            "A battered brass lantern, its glass cloudy with age. "
            "Oil sloshes inside — it still has fuel. "
            "The hinge is bent but the flame burns steady."
        ),
    },
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Item viewer demo")
    parser.add_argument(
        "--item",
        choices=list(DEMO_ITEMS.keys()),
        default="amulet",
        help="Which demo item to show (default: amulet)",
    )
    parser.add_argument(
        "--style",
        default="default",
        help="Pipeline style profile (default: default)",
    )
    parser.add_argument(
        "--image",
        help="Skip generation: provide path to an existing image file",
    )
    args = parser.parse_args()

    item = DEMO_ITEMS[args.item]
    image_path = Path(args.image) if args.image else None

    print(f"Showing item: {item['name']}")
    if image_path:
        print(f"Using image:  {image_path}")
    else:
        print("Generating image via pipeline…  (ComfyUI must be running)")

    show_item(
        name=item["name"],
        description=item["description"],
        style=args.style,
        image_path=image_path,
    )


if __name__ == "__main__":
    main()
