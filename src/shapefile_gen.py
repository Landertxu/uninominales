"""Shapefile generator for election results.

Reads the template census-section shapefile and produces an output shapefile
with constituency (CIRC) and winning party (PARTIDO) columns.

Also appends precomputed hole-filler polygons (unpopulated areas not covered by
any census section) assigned to their nearest neighboring constituency.
"""

import os
import shutil
import warnings

import shapefile
import yaml
from shapely import wkt
from shapely.geometry import Polygon, MultiPolygon


DEFAULT_HOLES_DIR = "data/geographic/spain2011/holes"


def load_holes(holes_dir=DEFAULT_HOLES_DIR):
    """Load hole assignments and geometries.

    Args:
        holes_dir: Directory containing hole_assignments.yaml and hole_geometries.wkt.

    Returns a list of (shapefile_shape, constituency_name) tuples.
    If either file is missing, returns an empty list.
    """
    assignments_path = os.path.join(holes_dir, "hole_assignments.yaml")
    geometries_path = os.path.join(holes_dir, "hole_geometries.wkt")

    if not os.path.exists(assignments_path):
        return []
    if not os.path.exists(geometries_path):
        return []

    with open(assignments_path) as f:
        data = yaml.safe_load(f)
    assignments = data.get("holes", {})

    holes = []
    with open(geometries_path) as f:
        for line in f:
            line = line.strip()
            if not line or "\t" not in line:
                continue
            hole_id, wkt_str = line.split("\t", 1)
            if hole_id not in assignments:
                continue
            circ = assignments[hole_id]["circ"]
            geom = wkt.loads(wkt_str)
            shp = _geometry_to_shape(geom)
            if shp is not None:
                holes.append((shp, circ))

    return holes


def _geometry_to_shape(geom):
    """Convert a shapely Polygon/MultiPolygon to a pyshp shape."""
    polygons = []
    if isinstance(geom, Polygon):
        polygons = [geom]
    elif isinstance(geom, MultiPolygon):
        polygons = list(geom.geoms)
    else:
        return None

    points = []
    parts = []
    for poly in polygons:
        if poly.is_empty:
            continue
        parts.append(len(points))
        # Exterior ring
        points.extend(list(poly.exterior.coords)[:-1])
        # Interior rings (holes within the filler polygon)
        for interior in poly.interiors:
            parts.append(len(points))
            points.extend(list(interior.coords)[:-1])

    if not points:
        return None

    return shapefile.Shape(shapefile.POLYGON, points=points, parts=parts)


def generate_shapefile(template_path, output_path, winners, valid, invalid,
                       holes_dir=DEFAULT_HOLES_DIR):
    """Generate an output shapefile with constituency and party columns.

    Args:
        template_path: Path to the template shapefile (without extension)
        output_path: Path for the output shapefile (without extension)
        winners: dict mapping constituency_name -> winning party
        valid: dict mapping province_code -> {constituency_name -> (inclusion_codes)}
        invalid: dict mapping province_code -> {constituency_name -> (exclusion_codes)}
        holes_dir: Directory containing hole-filler assignment files
    """
    sf = shapefile.Reader(template_path, encoding="latin-1")
    w = shapefile.Writer(output_path)
    w.fields = list(sf.fields)
    w.field("CIRC", "C", "40")
    w.field("PARTIDO", "C", "40")

    # Find the CUSEC field index by name
    # Note: sf.fields includes DeletionFlag at index 0, but records don't include it
    # So we need to subtract 1 from the field index to get the record index
    field_names = [field[0] for field in sf.fields]
    cusec_idx = field_names.index("CUSEC") - 1

    i = 0
    unmatched = 0
    shapes = sf.shapes()
    records = sf.records()
    # Save a clean copy of the first template record before the loop modifies it.
    # Used as a template for hole-filler polygon records.
    clean_base_rec = list(records[0])
    for shp, rec in zip(shapes, records):
        code = rec[cusec_idx]  # INE section code
        codpr = code[:2]  # Province code

        circ = f"resto{i}"
        i += 1

        if codpr in valid:
            for ncirc, tup in valid[codpr].items():
                if any(code.startswith(t) for t in tup):
                    exc_tup = invalid[codpr].get(ncirc, ())
                    if not any(code.startswith(e) for e in exc_tup):
                        circ = ncirc
                        break
            else:
                unmatched += 1

        w.shape(shp)
        rec.append(circ)
        rec.append(winners.get(circ, "0"))
        w.record(*rec)

    # Append hole-filler polygons.
    holes = load_holes(holes_dir)
    if holes:
        for hole_shp, circ in holes:
            w.shape(hole_shp)
            hole_rec = list(clean_base_rec)
            hole_rec.append(circ)
            hole_rec.append(winners.get(circ, "0"))
            w.record(*hole_rec)

    w.close()

    if unmatched:
        warnings.warn(
            f"{unmatched} census sections in covered provinces "
            f"matched no constituency",
            stacklevel=2,
        )

    # Copy .prj so the output shapefile has a valid CRS
    prj_src = template_path + ".prj"
    prj_dst = output_path + ".prj"
    if os.path.isfile(prj_src) and not os.path.isfile(prj_dst):
        shutil.copy2(prj_src, prj_dst)
