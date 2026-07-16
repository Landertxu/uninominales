"""Canary Islands relocation transform."""

from .config import CANARIAS_PROVS


def compute_canarias_transform(mainland_x, mainland_y, canarias_x, canarias_y):
    """Compute the translation to move Canary Islands to bottom-left of mainland.

    Returns (dx, dy) translation, or (0, 0) if no Canary Islands data.
    """
    if not canarias_x:
        return 0, 0

    canarias_cx = (min(canarias_x) + max(canarias_x)) / 2
    canarias_cy = (min(canarias_y) + max(canarias_y)) / 2
    canarias_w = max(canarias_x) - min(canarias_x)
    canarias_h = max(canarias_y) - min(canarias_y)

    target_right = min(mainland_x) - (max(mainland_x) - min(mainland_x)) * 0.02
    target_cx = target_right - canarias_w / 2
    target_cy = min(mainland_y) + canarias_h / 2

    dx = target_cx - canarias_cx
    dy = target_cy - canarias_cy

    return dx, dy


def split_mainland_canarias(sf):
    """Separate shapefile points into mainland and Canary Islands.

    Returns (mainland_x, mainland_y, canarias_x, canarias_y) coordinate lists.
    """
    mainland_x, mainland_y = [], []
    canarias_x, canarias_y = [], []

    for shp, rec in zip(sf.iterShapes(), sf.records()):
        code = rec[1]
        for x, y in shp.points:
            if code[:2] in CANARIAS_PROVS:
                canarias_x.append(x)
                canarias_y.append(y)
            else:
                mainland_x.append(x)
                mainland_y.append(y)

    return mainland_x, mainland_y, canarias_x, canarias_y


def draw_canarias_rectangle(draw, circ_data, project_fn):
    """Draw rectangle around Canary Islands on the main map."""
    canarias_proj_x, canarias_proj_y = [], []

    for circ, data in circ_data.items():
        for shp, province in data["shapes"]:
            if province in CANARIAS_PROVS:
                parts = list(shp.parts) + [len(shp.points)]
                for j in range(len(parts) - 1):
                    ring = shp.points[parts[j]:parts[j + 1]]
                    for x, y in ring:
                        px, py = project_fn(x, y, province)
                        canarias_proj_x.append(px)
                        canarias_proj_y.append(py)

    if canarias_proj_x:
        from .config import INSET_BORDER_COLOR
        margin = 15
        rx_min = min(canarias_proj_x) - margin
        rx_max = max(canarias_proj_x) + margin
        ry_min = min(canarias_proj_y) - margin
        ry_max = max(canarias_proj_y) + margin
        draw.rectangle([rx_min, ry_min, rx_max, ry_max],
                       outline=INSET_BORDER_COLOR, width=2)
