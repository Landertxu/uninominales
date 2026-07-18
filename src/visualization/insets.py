"""Inset maps for cities (Madrid, Barcelona)."""

from PIL import Image, ImageDraw

from .config import (PARTY_COLORS, DEFAULT_COLOR, BG_COLOR, BORDER_COLOR,
                     INSET_BORDER_COLOR, INSETS, CANARIAS_PROVS)
from .core import get_bbox


def make_inset_project(bb_xmin, bb_ymin, inset_scale, inset_offset_x,
                       inset_offset_y, inset_h):
    """Create a projection function for an inset map."""
    def proj(x, y):
        px = int(inset_offset_x + (x - bb_xmin) * inset_scale)
        py = int(inset_h + inset_offset_y - (y - bb_ymin) * inset_scale)
        return (px, py)
    return proj


def render_inset(circ_data, circ_colors, prov_code, bb_xmin, bb_ymin,
                 bb_w, bb_h, inset_w, inset_h):
    """Render an inset map for a specific province.

    Returns the inset image.
    """
    inset_scale = min(inset_w / bb_w, inset_h / bb_h)
    inset_offset_x = (inset_w - bb_w * inset_scale) / 2
    inset_offset_y = (inset_h - bb_h * inset_scale) / 2

    inset_project = make_inset_project(bb_xmin, bb_ymin, inset_scale,
                                       inset_offset_x, inset_offset_y, inset_h)

    # Draw with party colors
    inset_img = Image.new("RGB", (inset_w, inset_h), BG_COLOR)
    inset_draw = ImageDraw.Draw(inset_img)

    for circ, data in circ_data.items():
        color = PARTY_COLORS.get(data["partido"], DEFAULT_COLOR)
        for shp, province in data["shapes"]:
            if province != prov_code:
                continue
            parts = list(shp.parts) + [len(shp.points)]
            for j in range(len(parts) - 1):
                ring = shp.points[parts[j]:parts[j + 1]]
                projected = [inset_project(x, y) for x, y in ring]
                if len(projected) >= 3:
                    inset_draw.polygon(projected, fill=color)

    # Draw borders using unique-color technique
    inset_circ_img = Image.new("RGB", (inset_w, inset_h), BG_COLOR)
    inset_circ_draw = ImageDraw.Draw(inset_circ_img)

    for circ, data in circ_data.items():
        ucolor = circ_colors[circ]
        for shp, province in data["shapes"]:
            if province != prov_code:
                continue
            parts = list(shp.parts) + [len(shp.points)]
            for j in range(len(parts) - 1):
                ring = shp.points[parts[j]:parts[j + 1]]
                projected = [inset_project(x, y) for x, y in ring]
                if len(projected) >= 3:
                    inset_circ_draw.polygon(projected, fill=ucolor, outline=ucolor)

    inset_pixels = inset_circ_img.load()
    for py in range(inset_h):
        for px in range(inset_w):
            c = inset_pixels[px, py]
            if c == BG_COLOR:
                continue
            if px + 1 < inset_w and inset_pixels[px + 1, py] != c:
                inset_img.putpixel((px, py), BORDER_COLOR)
            if py + 1 < inset_h and inset_pixels[px, py + 1] != c:
                inset_img.putpixel((px, py), BORDER_COLOR)

    return inset_img


def draw_insets(main_img, draw, circ_data, circ_colors, project_fn,
                width, height, padding, top_margin=120):
    """Draw all configured inset maps onto the main image.

    Also draws extent squares and connector lines.
    """
    for prov_code, config in INSETS.items():
        pos = config["pos"]
        zoom = config.get("zoom", 1)
        center_x, center_y = config.get("center", None)

        # Get bounding box for this province's shapes
        prov_shapes = []
        for circ, data in circ_data.items():
            for shp, province in data["shapes"]:
                if province == prov_code:
                    prov_shapes.append(shp)

        if not prov_shapes:
            continue

        bbox = get_bbox(prov_shapes)
        if bbox is None:
            continue

        bb_xmin, bb_ymin, bb_xmax, bb_ymax = bbox
        bb_w = bb_xmax - bb_xmin
        bb_h = bb_ymax - bb_ymin

        # Use specified center or default to bbox center
        if center_x is not None:
            bb_cx, bb_cy = center_x, center_y
        else:
            bb_cx = (bb_xmin + bb_xmax) / 2
            bb_cy = (bb_ymin + bb_ymax) / 2

        # Apply zoom: shrink bbox around the center
        bb_w /= zoom
        bb_h /= zoom
        bb_xmin = bb_cx - bb_w / 2
        bb_xmax = bb_cx + bb_w / 2
        bb_ymin = bb_cy - bb_h / 2
        bb_ymax = bb_cy + bb_h / 2

        # Add small margin
        margin_frac = 0.1
        bb_xmin -= bb_w * margin_frac
        bb_xmax += bb_w * margin_frac
        bb_ymin -= bb_h * margin_frac
        bb_ymax += bb_h * margin_frac
        bb_w = bb_xmax - bb_xmin
        bb_h = bb_ymax - bb_ymin

        # Inset size
        inset_w = 220
        inset_h = int(inset_w * bb_h / bb_w)
        if inset_h > 250:
            inset_h = 250
            inset_w = int(inset_h * bb_w / bb_h)

        # Calculate inset position on main image
        if pos == "left":
            ix = padding + 10
            iy = padding + top_margin + 20
        elif pos == "left_lower":
            ix = padding + 10
            iy = padding + top_margin + inset_h + 60
        elif pos == "right":
            ix = width - padding - inset_w - 10
            iy = height // 2 - inset_h // 2
        elif pos == "top_left":
            ix = padding + 10
            iy = padding + 10
        elif pos == "top_right":
            ix = width - padding - inset_w - 10
            iy = padding + 10
        elif pos == "bottom_left":
            ix = padding + 10
            iy = height - padding - 50 - inset_h - 10
        elif pos == "bottom_right":
            ix = width - padding - inset_w - 10
            iy = height - padding - 50 - inset_h - 10
        else:
            continue

        # Render the inset
        inset_img = render_inset(circ_data, circ_colors, prov_code,
                                 bb_xmin, bb_ymin, bb_w, bb_h,
                                 inset_w, inset_h)

        # Draw border rectangle around inset
        inset_draw_final = ImageDraw.Draw(inset_img)
        inset_draw_final.rectangle([0, 0, inset_w - 1, inset_h - 1],
                                   outline=INSET_BORDER_COLOR, width=2)

        # Paste inset onto main image
        main_img.paste(inset_img, (ix, iy))

        # Draw connector line from inset to city center on main map
        main_cx, main_cy = project_fn(bb_cx, bb_cy)

        # Connector line start point (edge of inset box closest to main map)
        if "top" in pos:
            line_start = (ix + inset_w // 2, iy + inset_h)
        elif "bottom" in pos:
            line_start = (ix + inset_w // 2, iy)
        elif "left" in pos:
            line_start = (ix + inset_w, iy + inset_h // 2)
        elif "right" in pos:
            line_start = (ix, iy + inset_h // 2)

        # Clamp main map point to be visible
        main_cx = max(padding, min(width - padding, main_cx))
        main_cy = max(padding + 50, min(height - padding - 50, main_cy))

        draw.line([line_start, (main_cx, main_cy)], fill=INSET_BORDER_COLOR, width=1)

        # Draw extent square on main map
        ext_tl = project_fn(bb_xmin, bb_ymax)
        ext_br = project_fn(bb_xmax, bb_ymin)
        draw.rectangle([ext_tl, ext_br], outline=INSET_BORDER_COLOR, width=2)
