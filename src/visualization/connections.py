"""Connection lines between separated constituencies."""

from collections import defaultdict

from .core import get_bbox


def find_polygon_groups(shapes, split_axis='y', threshold=None):
    """Find separate polygon groups within a constituency.
    
    Returns list of list of polygon centroids for each group.
    """
    polygons = []
    for shp in shapes:
        parts = list(shp.parts) + [len(shp.points)]
        for j in range(len(parts) - 1):
            ring = shp.points[parts[j]:parts[j+1]]
            xs = [p[0] for p in ring]
            ys = [p[1] for p in ring]
            cx = sum(xs) / len(xs)
            cy = sum(ys) / len(ys)
            polygons.append((cx, cy))
    
    if len(polygons) <= 1:
        return []
    
    # Get coordinates along split axis
    if split_axis == 'y':
        coords = [p[1] for p in polygons]
    else:
        coords = [p[0] for p in polygons]
    
    coords.sort()
    
    # Find largest gap
    max_gap = 0
    gap_pos = 0
    for i in range(1, len(coords)):
        gap = coords[i] - coords[i-1]
        if gap > max_gap:
            max_gap = gap
            gap_pos = (coords[i-1] + coords[i]) / 2
    
    # Only split if gap is significant
    if threshold is None:
        threshold = max_gap * 0.5
    if max_gap < threshold:
        return []
    
    # Split polygons into groups
    group1 = [p for p in polygons if (p[1] if split_axis == 'y' else p[0]) <= gap_pos]
    group2 = [p for p in polygons if (p[1] if split_axis == 'y' else p[0]) > gap_pos]
    
    if not group1 or not group2:
        return []
    
    # Return centroids of each group
    centroids = []
    for group in [group1, group2]:
        cx = sum(p[0] for p in group) / len(group)
        cy = sum(p[1] for p in group) / len(group)
        centroids.append((cx, cy))
    
    return centroids


def find_bounding_box(shapes, padding=0):
    """Find the bounding box of all shapes with optional padding."""
    bbox = get_bbox(shapes)
    if bbox is None:
        return None
    min_x, min_y, max_x, max_y = bbox
    return (min_x - padding, min_y - padding, max_x + padding, max_y + padding)


def draw_connection_lines(draw, circ_data, project_fn):
    """Draw connection lines between separated constituencies.
    
    For multi-island constituencies, draws a rectangle around all islands.
    """
    # Group shapes by CIRC
    circ_shapes = defaultdict(list)
    for circ, data in circ_data.items():
        for shp, province in data["shapes"]:
            circ_shapes[circ].append(shp)
    
    line_color = (100, 100, 100)
    
    # Ibiza-Formentera (baleares7): split by y-axis gap
    baleares7_shapes = circ_shapes.get('baleares7', [])
    if baleares7_shapes:
        groups = find_polygon_groups(baleares7_shapes, split_axis='y', threshold=5000)
        if len(groups) == 2:
            # Draw rectangle around both islands
            min_x, min_y, max_x, max_y = find_bounding_box(baleares7_shapes, padding=10000)
            
            corners = [
                project_fn(min_x, min_y),
                project_fn(max_x, min_y),
                project_fn(max_x, max_y),
                project_fn(min_x, max_y),
            ]
            
            # Draw thin rectangle
            for i in range(4):
                x1, y1 = corners[i]
                x2, y2 = corners[(i+1) % 4]
                draw.line([(x1, y1), (x2, y2)], fill=line_color, width=1)
    
    # Canary Islands: tenerife8 spans La Palma + La Gomera + El Hierro
    # Split by y-axis (El Hierro is south, La Palma/La Gomera are north)
    tenerife8_shapes = circ_shapes.get('tenerife8', [])
    if tenerife8_shapes:
        groups = find_polygon_groups(tenerife8_shapes, split_axis='y', threshold=30000)
        if len(groups) >= 2:
            # Draw smaller rectangle around La Palma + La Gomera + El Hierro
            min_x, min_y, max_x, max_y = find_bounding_box(tenerife8_shapes, padding=20000)
            
            corners = [
                project_fn(min_x, min_y, '38'),
                project_fn(max_x, min_y, '38'),
                project_fn(max_x, max_y, '38'),
                project_fn(min_x, max_y, '38'),
            ]
            
            # Draw thin rectangle
            for i in range(4):
                x1, y1 = corners[i]
                x2, y2 = corners[(i+1) % 4]
                draw.line([(x1, y1), (x2, y2)], fill=line_color, width=1)
