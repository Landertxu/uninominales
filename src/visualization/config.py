"""Party colors and map constants."""

import os
import yaml


def _hex_to_rgb(hex_color):
    """Convert hex color string to RGB tuple."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def _load_party_colors():
    """Load party colors from central YAML file."""
    path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "partidos", "parties.yaml")
    try:
        with open(path) as f:
            data = yaml.safe_load(f)
        colors = {}
        for name, info in data.items():
            hex_color = info.get("color", "#B4B4B4")
            colors[name] = _hex_to_rgb(hex_color)
        return colors
    except FileNotFoundError:
        return {}


PARTY_COLORS = _load_party_colors()

DEFAULT_COLOR = (200, 200, 200)
BG_COLOR = (255, 255, 255)
BORDER_COLOR = (50, 50, 50)
INSET_BORDER_COLOR = (80, 80, 80)

CANARIAS_PROVS = {"35", "38"}

# Inset configuration
# center: (x, y) in geographic coords to center the inset on
# zoom: extra zoom factor (1 = fit whole province, 5 = 5x zoomed in)
# pos: position on main image (left, right, top_left, top_right, bottom_left, bottom_right)
INSETS = {
    "28": {"pos": "left", "zoom": 4, "center": (440390, 4480969)},
    "08": {"pos": "bottom_right", "zoom": 4, "center": (926661, 4597229)},
}
