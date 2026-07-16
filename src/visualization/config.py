"""Party colors and map constants."""

PARTY_COLORS = {
    "PP": (0, 112, 192),
    "PSOE": (228, 26, 28),
    "C's": (255, 127, 0),
    "P's": (178, 24, 43),
    "IU": (51, 160, 44),
    "ERC": (255, 204, 0),
    "PNV": (0, 128, 128),
    "DL": (106, 61, 154),
    "UPyD": (255, 127, 14),
    "BNG": (177, 89, 40),
    "CC": (0, 160, 200),
    "Compromis": (255, 210, 0),
    "EH Bildu": (0, 153, 136),
    "Nueva Canarias": (255, 195, 0),
    "R": (180, 180, 180),
    "0": (220, 220, 220),
}

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
