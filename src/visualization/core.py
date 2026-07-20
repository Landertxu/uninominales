"""Core map rendering utilities."""

import random
from collections import defaultdict
from PIL import Image, ImageDraw

from .config import PARTY_COLORS, DEFAULT_COLOR, BG_COLOR, BORDER_COLOR


def get_bbox(shapes_iter):
    """Get bounding box from an iterable of shapefile shapes."""
    xs, ys = [], []
    for shp in shapes_iter:
        for x, y in shp.points:
            xs.append(x)
            ys.append(y)
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def group_by_circ(sf):
    """Group shapefile records by CIRC field.

    Returns circ_data dict mapping circ -> {"shapes": [(shp, province)], "partido": str}
    """
    circ_data = defaultdict(lambda: {"shapes": [], "partido": "0"})
    for shp, rec in zip(sf.iterShapes(), sf.records()):
        circ = rec[-2]
        partido = rec[-1] if rec[-1] else "0"
        province = rec[1][:2]
        circ_data[circ]["shapes"].append((shp, province))
        circ_data[circ]["partido"] = partido
    return circ_data


def count_representatives(circ_data):
    """Count representatives per party."""
    rep_counts = defaultdict(int)
    for circ, data in circ_data.items():
        rep_counts[data["partido"]] += 1
    return rep_counts


def assign_unique_colors(circ_data):
    """Assign a unique color to each CIRC for border detection."""
    random.seed(42)
    circ_colors = {}
    used = set()
    for circ in sorted(circ_data.keys()):
        while True:
            c = (random.randint(1, 254), random.randint(1, 254), random.randint(1, 254))
            if c not in used and c != BG_COLOR:
                circ_colors[circ] = c
                used.add(c)
                break
    return circ_colors


def detect_borders(circ_img):
    """Detect borders where different colors meet. Returns set of (px, py)."""
    pixels = circ_img.load()
    w, h = circ_img.size
    border_mask = set()

    for py in range(h):
        for px in range(w):
            c = pixels[px, py]
            if c == BG_COLOR:
                continue
            if px + 1 < w and pixels[px + 1, py] != c:
                border_mask.add((px, py))
            if py + 1 < h and pixels[px, py + 1] != c:
                border_mask.add((px, py))

    return border_mask


def draw_constituencies(img, circ_data, circ_colors, project_fn):
    """Draw constituencies with unique colors for border detection.

    Returns the image with unique-colored constituencies drawn.
    """
    circ_img = Image.new("RGB", img.size, BG_COLOR)
    circ_draw = ImageDraw.Draw(circ_img)

    for circ, data in circ_data.items():
        ucolor = circ_colors[circ]
        for shp, province in data["shapes"]:
            parts = list(shp.parts) + [len(shp.points)]
            for j in range(len(parts) - 1):
                ring = shp.points[parts[j]:parts[j + 1]]
                projected = [project_fn(x, y, province) for x, y in ring]
                if len(projected) >= 3:
                    circ_draw.polygon(projected, fill=ucolor, outline=ucolor)

    return circ_img


def draw_main_map(img, circ_data, project_fn):
    """Draw constituencies with party colors."""
    draw = ImageDraw.Draw(img)

    for circ, data in circ_data.items():
        color = PARTY_COLORS.get(data["partido"], DEFAULT_COLOR)
        for shp, province in data["shapes"]:
            parts = list(shp.parts) + [len(shp.points)]
            for j in range(len(parts) - 1):
                ring = shp.points[parts[j]:parts[j + 1]]
                projected = [project_fn(x, y, province) for x, y in ring]
                if len(projected) >= 3:
                    draw.polygon(projected, fill=color, outline=color)

    return draw


def apply_borders(img, border_mask):
    """Draw border pixels on the image."""
    for px, py in border_mask:
        img.putpixel((px, py), BORDER_COLOR)


def draw_legend(draw, rep_counts, width, height, padding, font):
    """Draw the party legend at the bottom of the image."""
    legend_y = height - 45
    legend_x = padding
    for party, count in sorted(rep_counts.items(), key=lambda x: -x[1]):
        color = PARTY_COLORS.get(party, DEFAULT_COLOR)
        draw.rectangle([legend_x, legend_y, legend_x + 14, legend_y + 14],
                       fill=color, outline=(0, 0, 0))
        text = f"{party}: {count}"
        draw.text((legend_x + 18, legend_y - 1), text, fill=(0, 0, 0), font=font)
        legend_x += font.getlength(text) + 35
        if legend_x > width - 120:
            legend_y += 22
            legend_x = padding
