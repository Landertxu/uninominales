"""Shapefile generator for election results.

Reads the template census-section shapefile and produces an output shapefile
with constituency (CIRC) and winning party (PARTIDO) columns.
"""

import shapefile


def _compute_centroid(points):
    """Compute centroid of a list of (x, y) points."""
    if not points:
        return (0, 0)
    x = sum(p[0] for p in points) / len(points)
    y = sum(p[1] for p in points) / len(points)
    return (x, y)


def _find_closest_constituency(centroid, circ_centroids):
    """Find the closest constituency to a given centroid.
    
    Args:
        centroid: (x, y) of the unassigned section
        circ_centroids: dict mapping constituency_name -> (x, y)
    
    Returns: closest constituency name
    """
    min_dist = float('inf')
    closest = None
    cx, cy = centroid
    
    for name, (ccx, ccy) in circ_centroids.items():
        # Skip "resto" constituencies
        if name.startswith("resto"):
            continue
        dist = (cx - ccx)**2 + (cy - ccy)**2
        if dist < min_dist:
            min_dist = dist
            closest = name
    
    return closest


def generate_shapefile(template_path, output_path, winners, valid, invalid):
    """Generate an output shapefile with constituency and party columns.

    Args:
        template_path: Path to the template shapefile (without extension)
        output_path: Path for the output shapefile (without extension)
        winners: dict mapping constituency_name -> winning party
        valid: dict mapping province_code -> {constituency_name -> (inclusion_codes)}
        invalid: dict mapping province_code -> {constituency_name -> (exclusion_codes)}
    """
    sf = shapefile.Reader(template_path, encoding="latin-1")
    w = shapefile.Writer(output_path)
    w.fields = list(sf.fields)
    w.field("CIRC", "C", "40")
    w.field("PARTIDO", "C", "40")

    # First pass: assign sections and track centroids
    circ_sections = {}  # circ -> list of section records
    circ_centroids = {}  # circ -> (cx, cy)
    resto_centroids = {}  # resto_id -> centroid
    
    i = 0
    assignments = []  # (shp, rec, circ, resto_id)
    
    for shp, rec in sf.iterShapes():
        code = rec[1]  # INE section code
        codpr = code[:2]  # Province code

        circ = f"resto{i}"
        resto_id = i
        i += 1

        if codpr in valid:
            for ncirc, tup in valid[codpr].items():
                if any(code.startswith(t) for t in tup):
                    exc_tup = invalid[codpr].get(ncirc, ())
                    if not any(code.startswith(e) for e in exc_tup):
                        circ = ncirc
                        resto_id = None
                        break

        # Track centroid
        points = []
        parts = list(shp.parts) + [len(shp.points)]
        for j in range(len(parts) - 1):
            ring = shp.points[parts[j]:parts[j+1]]
            points.extend(ring)
        
        centroid = _compute_centroid(points)
        
        if circ.startswith("resto"):
            resto_centroids[resto_id] = centroid
        else:
            if circ not in circ_centroids:
                circ_centroids[circ] = []
            circ_centroids[circ].append(centroid)
        
        assignments.append((shp, rec, circ, resto_id))
    
    # Compute average centroids for assigned constituencies
    avg_centroids = {}
    for circ, centroids in circ_centroids.items():
        x = sum(c[0] for c in centroids) / len(centroids)
        y = sum(c[1] for c in centroids) / len(centroids)
        avg_centroids[circ] = (x, y)
    
    # Second pass: reassign "resto" sections to closest neighbor
    final_assignments = []
    for shp, rec, circ, resto_id in assignments:
        if circ.startswith("resto") and resto_id in resto_centroids:
            centroid = resto_centroids[resto_id]
            closest = _find_closest_constituency(centroid, avg_centroids)
            if closest:
                circ = closest
        
        final_assignments.append((shp, rec, circ))
    
    # Third pass: write output
    for shp, rec, circ in final_assignments:
        w.shape(shp)
        rec.append(circ)
        rec.append(winners.get(circ, "0"))
        w.record(*rec)

    w.close()
