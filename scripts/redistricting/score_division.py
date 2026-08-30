"""Score an existing constituency division against the fitness function.

Example:
    python scripts/redistricting/score_division.py \
        --population data/census/spain2011/population/2011.csv \
        --constituencies data/geographic/spain2011/constituencies \
        --shapefile data/geographic/spain2011/geographic/SECC_CPV_E_20111101_01_R_INE
"""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.redistricting.geometry import load_shapefile
from scripts.redistricting.loader import load_division, load_population
from scripts.redistricting.scorer import score_province


def print_report(report):
    """Print a human-readable report."""
    print("=" * 70)
    print("Constituency division score report")
    print("=" * 70)

    total_penalty = sum(r["total_penalty"] for r in report)
    print(f"\nNationwide total penalty: {total_penalty:.2f}")
    print()

    for r in sorted(report, key=lambda x: x["total_penalty"], reverse=True):
        print(f"Province {r['province']}: "
              f"{r['seats']} seats, "
              f"pop {r['total_population']:,}, "
              f"ideal {r['ideal_population']:.0f}")
        print(f"  population penalty:       {r['population_penalty']:.2f}")
        print(f"  municipality splits:      {r['municipality_split_penalty']}")
        print(f"  district splits:          {r['district_split_penalty']}")
        print(f"  contiguity penalty:       {r['contiguity_penalty']:.2f}")
        print(f"  compactness penalty:      {r['compactness_penalty']:.2f}")
        print(f"  total penalty:            {r['total_penalty']:.2f}")
        print()


def main():
    parser = argparse.ArgumentParser(description="Score a constituency division")
    parser.add_argument(
        "--population",
        default=str(PROJECT_ROOT / "data" / "census" / "spain2011" / "population" / "2011.csv"),
        help="Path to population CSV",
    )
    parser.add_argument(
        "--constituencies",
        default=str(PROJECT_ROOT / "data" / "geographic" / "spain2011" / "constituencies"),
        help="Directory with constituency .dat files",
    )
    parser.add_argument(
        "--shapefile",
        default=str(PROJECT_ROOT / "data" / "geographic" / "spain2011" / "geographic" / "SECC_CPV_E_20111101_01_R_INE"),
        help="Shapefile prefix (without extension). If omitted, geometry metrics are skipped.",
    )
    parser.add_argument(
        "--no-geometry",
        action="store_true",
        help="Skip geometry-based metrics (contiguity and compactness)",
    )
    args = parser.parse_args()

    population = load_population(args.population)
    division = load_division(args.constituencies)

    section_geoms = None
    adjacency = None
    if not args.no_geometry:
        print("Loading shapefile and building adjacency graph...")
        section_geoms, adjacency = load_shapefile(args.shapefile)
        print(f"Loaded {len(section_geoms)} sections.")
        print()

    report = []
    for province_code, constituencies in sorted(division.items()):
        province_report = score_province(
            province_code, constituencies, population, section_geoms, adjacency
        )
        report.append(province_report)

    print_report(report)


if __name__ == "__main__":
    main()
