#!/usr/bin/env python3
"""Find interior holes in the template census-section shapefile.

Computes the union of all census-section polygons for the entire country and
extracts the interior rings (holes). Each hole is then assigned to the
neighboring constituency that shares the longest border with it.

This catches holes that span multiple provinces, which a per-province union
would miss because the hole touches the shared province border.

Outputs:
    data/mapas/hole_assignments.yaml  -- maps hole_id -> constituency
    data/mapas/hole_geometries.wkt    -- WKT geometry cache for each hole
"""

import os
import sys
from collections import defaultdict

import shapefile
import yaml
from shapely.geometry import shape, mapping, Polygon
from shapely.ops import unary_union
from shapely import length, boundary
from shapely.strtree import STRtree

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.constituency_parser import parse_constituency_file


TEMPLATE_SHP = "data/mapas/molde/SECC_CPV_E_20111101_01_R_INE"
CIRC_DIR = "data/circunscripciones"
ASSIGNMENTS_PATH = "data/mapas/hole_assignments.yaml"
GEOMETRIES_PATH = "data/mapas/hole_geometries.wkt"


def load_constituencies(circ_dir):
    """Load all constituency definitions.

    Returns (valid, invalid) where:
      valid[province_code][constituency_name] = (inclusion_codes,)
      invalid[province_code][constituency_name] = (exclusion_codes,)
    """
    valid = defaultdict(dict)
    invalid = defaultdict(dict)

    for filename in sorted(os.listdir(circ_dir)):
        if not filename.startswith("circ") or not filename.endswith(".dat"):
            continue
        province_code = filename.replace("circ", "").replace(".dat", "")
        filepath = os.path.join(circ_dir, filename)
        for name, inclusions, exclusions in parse_constituency_file(filepath):
            valid[province_code][name] = tuple(inclusions)
            invalid[province_code][name] = tuple(exclusions)

    return valid, invalid


def find_constituency(code, province_code, valid, invalid):
    """Return the constituency name for a census section code."""
    if province_code not in valid:
        return None
    for ncirc, tup in valid[province_code].items():
        if any(code.startswith(t) for t in tup):
            exc_tup = invalid[province_code].get(ncirc, ())
            if not any(code.startswith(e) for e in exc_tup):
                return ncirc
    return None


def iter_interior_rings(geom):
    """Yield all interior rings from a Polygon or MultiPolygon."""
    if geom.is_empty:
        return
    if geom.geom_type == "Polygon":
        for ring in geom.interiors:
            yield ring
    elif geom.geom_type == "MultiPolygon":
        for poly in geom.geoms:
            for ring in poly.interiors:
                yield ring


def main():
    print("Loading constituency definitions...")
    valid, invalid = load_constituencies(CIRC_DIR)

    print("Loading template shapefile...")
    sf = shapefile.Reader(TEMPLATE_SHP, encoding="latin-1")

    print(f"Read {len(sf.shapes())} census sections")

    # Convert all shapes to shapely geometries and assign constituencies.
    section_polys = []
    section_circs = []
    section_codes = []
    section_provinces = []

    for shp, rec in zip(sf.shapes(), sf.records()):
        code = rec[1]
        province = code[:2]
        circ = find_constituency(code, province, valid, invalid)
        geom = shape(shp.__geo_interface__)
        if geom.is_empty:
            continue
        section_polys.append(geom)
        section_circs.append(circ)
        section_codes.append(code)
        section_provinces.append(province)

    print(f"Built {len(section_polys)} geometries")

    # Build a spatial index over all section geometries.
    tree = STRtree(section_polys)

    print("Computing national union and extracting holes...")
    national_union = unary_union(section_polys)

    assignments = {}
    geometries = {}
    hole_counter = 0

    for ring in iter_interior_rings(national_union):
        hole = Polygon(ring)
        if hole.is_empty:
            continue

        # Find candidate neighbors whose bounding box intersects the hole.
        candidate_indices = tree.query(hole)

        # Measure shared border length with each constituency.
        border_lengths = defaultdict(float)
        for idx in candidate_indices:
            candidate = section_polys[idx]
            if not candidate.touches(hole):
                continue
            circ = section_circs[idx]
            if circ is None:
                continue
            shared = boundary(candidate).intersection(boundary(hole))
            if shared.is_empty:
                continue
            border_lengths[circ] += float(length(shared))

        if not border_lengths:
            continue

        best_circ = max(border_lengths, key=border_lengths.get)
        # Determine the province of the winning neighbor for metadata.
        best_idx = next(
            idx for idx in candidate_indices
            if section_circs[idx] == best_circ
            and section_polys[idx].touches(hole)
        )
        best_province = section_provinces[best_idx]

        hole_id = f"hole_{hole_counter:05d}"
        hole_counter += 1

        assignments[hole_id] = {
            "province": best_province,
            "circ": best_circ,
            "area_m2": float(hole.area),
            "border_lengths": dict(sorted(
                border_lengths.items(), key=lambda x: -x[1]
            )),
        }
        geometries[hole_id] = hole.wkt

    print(f"\nFound {len(assignments)} holes")

    os.makedirs(os.path.dirname(ASSIGNMENTS_PATH), exist_ok=True)

    with open(ASSIGNMENTS_PATH, "w") as f:
        yaml.safe_dump(
            {"holes": assignments},
            f,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
        )
    print(f"Saved assignments to {ASSIGNMENTS_PATH}")

    with open(GEOMETRIES_PATH, "w") as f:
        for hole_id, wkt in geometries.items():
            f.write(f"{hole_id}\t{wkt}\n")
    print(f"Saved geometries to {GEOMETRIES_PATH}")


if __name__ == "__main__":
    main()
