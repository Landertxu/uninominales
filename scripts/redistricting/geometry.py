"""Geometry helpers for constituency scoring and optimization."""

import sys
from pathlib import Path

import shapefile
from shapely.geometry import shape
from shapely.ops import unary_union
from shapely.strtree import STRtree

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def load_shapefile(shapefile_prefix):
    """Load census-section geometry from a shapefile prefix.

    Returns (section_geoms, adjacency) where:
      - section_geoms: dict mapping CUSEC -> shapely geometry
      - adjacency: dict mapping CUSEC -> set of adjacent CUSEC codes
    """
    shp_path = f"{shapefile_prefix}.shp"
    sf = shapefile.Reader(shp_path, encoding="latin-1")

    section_geoms = {}
    cusecs = []
    geometries = []

    for record in sf.shapeRecords():
        cusec = record.record["CUSEC"]
        polygon = shape(record.shape.__geo_interface__)
        section_geoms[cusec] = polygon
        cusecs.append(cusec)
        geometries.append(polygon)

    tree = STRtree(geometries)

    adjacency = {cusec: set() for cusec in section_geoms}

    for cusec, polygon in section_geoms.items():
        candidate_indices = tree.query(polygon)
        for idx in candidate_indices:
            candidate_cusec = cusecs[idx]
            if candidate_cusec == cusec:
                continue
            candidate = section_geoms[candidate_cusec]
            if polygon.touches(candidate) or polygon.intersects(candidate.boundary):
                adjacency[cusec].add(candidate_cusec)

    return section_geoms, adjacency


def connected_components(nodes, adjacency):
    """Return the number of connected components among nodes."""
    nodes = set(nodes)
    visited = set()
    components = 0

    for start in nodes:
        if start in visited:
            continue
        components += 1
        stack = [start]
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            for neighbor in adjacency.get(current, set()):
                if neighbor in nodes and neighbor not in visited:
                    stack.append(neighbor)

    return components


def union_area_and_perimeter(section_geoms, sections):
    """Compute area and perimeter of the union of a set of sections."""
    geoms = [section_geoms[s] for s in sections if s in section_geoms]
    if not geoms:
        return 0.0, 0.0

    union = unary_union(geoms)
    return float(union.area), float(union.length)
