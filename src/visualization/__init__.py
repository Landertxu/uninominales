"""Election map visualization.

Renders an election shapefile to a PNG image with:
- Party-colored constituencies
- Border detection between constituencies
- Canary Islands relocated to bottom-left corner
- Inset maps for Madrid and Barcelona
- Legend showing seat counts by party
"""

from PIL import Image, ImageFont
import shapefile

from .config import (BG_COLOR, BORDER_COLOR, CANARIAS_PROVS,
                     INSET_BORDER_COLOR, INSETS)
from .core import (get_bbox, group_by_circ, count_representatives,
                   assign_unique_colors, draw_constituencies, detect_borders,
                   draw_main_map, apply_borders, draw_legend)
from .canarias import (split_mainland_canarias, compute_canarias_transform,
                       draw_canarias_rectangle)
from .insets import draw_insets
from .connections import draw_connection_lines


def render_map(shapefile_path, output_path, width=1100, height=900, padding=15):
    """Render an election shapefile to a PNG image.

    Args:
        shapefile_path: Path to the input .shp file
        output_path: Path for the output PNG file
        width: Image width in pixels
        height: Image height in pixels
        padding: Padding around the map in pixels
    """
    sf = shapefile.Reader(shapefile_path, encoding="latin-1")

    # Separate mainland and Canary Islands
    mainland_x, mainland_y, canarias_x, canarias_y = split_mainland_canarias(sf)

    # Compute Canary Islands transform
    canarias_dx, canarias_dy = compute_canarias_transform(
        mainland_x, mainland_y, canarias_x, canarias_y
    )

    # Compute effective bounding box
    all_x = list(mainland_x)
    all_y = list(mainland_y)
    if canarias_x:
        for x, y in zip(canarias_x, canarias_y):
            all_x.append(x + canarias_dx)
            all_y.append(y + canarias_dy)

    x_min, x_max = min(all_x), max(all_x)
    y_min, y_max = min(all_y), max(all_y)

    # Calculate scaling - extra space at top for insets
    map_w = x_max - x_min
    map_h = y_max - y_min
    top_margin = 80  # Extra space for top insets
    img_w = width - 2 * padding
    img_h = height - 2 * padding - 50 - top_margin
    scale = min(img_w / map_w, img_h / map_h)

    # Center the map
    offset_x = padding + (img_w - map_w * scale) / 2
    offset_y = padding + top_margin + (img_h - map_h * scale) / 2 + 50

    def project(x, y, province_code=None):
        if province_code in CANARIAS_PROVS and canarias_x:
            x += canarias_dx
            y += canarias_dy
        px = int(offset_x + (x - x_min) * scale)
        py = int(height - offset_y - (y - y_min) * scale)
        return (px, py)

    # Prepare data
    circ_data = group_by_circ(sf)
    rep_counts = count_representatives(circ_data)
    circ_colors = assign_unique_colors(circ_data)

    # Draw main map with unique colors for border detection
    circ_img = draw_constituencies(
        Image.new("RGB", (width, height), BG_COLOR),
        circ_data, circ_colors, project
    )
    border_mask = detect_borders(circ_img)

    # Draw final image with party colors
    img = Image.new("RGB", (width, height), BG_COLOR)
    draw = draw_main_map(img, circ_data, project)
    apply_borders(img, border_mask)

    # Draw Canary Islands rectangle
    draw_canarias_rectangle(draw, circ_data, project)

    # Draw connection lines between separated constituencies
    draw_connection_lines(draw, circ_data, project)

    # Draw inset maps
    draw_insets(img, draw, circ_data, circ_colors, project,
                width, height, padding, top_margin)

    # Load font
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
    except (OSError, IOError):
        font = ImageFont.load_default()

    # Draw legend
    draw_legend(draw, rep_counts, width, height, padding, font)

    img.save(output_path)
    print(f"Saved to {output_path}")
