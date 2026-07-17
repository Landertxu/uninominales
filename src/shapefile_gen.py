"""Shapefile generator for election results.

Reads the template census-section shapefile and produces an output shapefile
with constituency (CIRC) and winning party (PARTIDO) columns.
"""

import shapefile


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

    i = 0
    for shp, rec in zip(sf.iterShapes(), sf.records()):
        code = rec[1]  # INE section code
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

        w.shape(shp)
        rec.append(circ)
        rec.append(winners.get(circ, "0"))
        w.record(*rec)

    w.close()
