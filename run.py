#!/usr/bin/env python3
"""Election simulator orchestrator.

Runs the complete workflow:
1. Load INE data into SQLite database
2. Run FPTP simulation for a given year
3. Generate output shapefile
4. Render the election map

Usage:
    python run.py                    # Full workflow for 2015
    python run.py --year 2015        # Specify year
    python run.py --skip-load        # Skip data loading (use existing DB)
    python run.py --skip-map         # Skip map generation
    python run.py --no-map           # Don't generate shapefile
    python run.py --viz-only         # Just render the map from existing shapefile
"""

import argparse
import os
import sqlite3

from src.db_loader import load_all_data
from src.election_runner import run_simulation
from src.shapefile_gen import generate_shapefile
from src.visualization import render_map

DB_PATH = "elecciones.db"
OUTPUT_DIR = "output"
TEMPLATE_SHP = "data/mapas/molde/SECC_CPV_E_20111101_01_R_INE"


def main():
    parser = argparse.ArgumentParser(
        description="Election simulator - FPTP system"
    )
    parser.add_argument(
        "--year", type=int, default=2015, choices=[2008, 2011, 2015],
        help="Election year to simulate (default: 2015)"
    )
    parser.add_argument(
        "--skip-load", action="store_true",
        help="Skip data loading, use existing database"
    )
    parser.add_argument(
        "--skip-map", action="store_true",
        help="Skip map rendering (generate shapefile only)"
    )
    parser.add_argument(
        "--no-map", action="store_true",
        help="Don't generate shapefile (print results only)"
    )
    parser.add_argument(
        "--viz-only", action="store_true",
        help="Just render the map from existing shapefile (fast)"
    )
    parser.add_argument(
        "--width", type=int, default=1100,
        help="Map image width (default: 1100)"
    )
    parser.add_argument(
        "--height", type=int, default=900,
        help="Map image height (default: 900)"
    )
    args = parser.parse_args()

    # Change to script directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # Viz-only mode: just render from existing shapefile
    if args.viz_only:
        shp_path = os.path.join(OUTPUT_DIR, f"mapa{args.year}.shp")
        if not os.path.exists(shp_path):
            print(f"Error: {shp_path} not found. Run full workflow first.")
            return
        img_path = os.path.join(OUTPUT_DIR, f"mapa{args.year}.png")
        render_map(shp_path, img_path, width=args.width, height=args.height)
        return

    # Step 1: Load data
    if not args.skip_load:
        print("=" * 60)
        print("Step 1: Loading election data into database")
        print("=" * 60)
        conn = load_all_data(DB_PATH)
    else:
        print("Skipping data loading, using existing database")
        conn = sqlite3.connect(DB_PATH)

    # Step 2: Run simulation
    print("\n" + "=" * 60)
    print(f"Step 2: Running FPTP simulation for {args.year}")
    print("=" * 60)
    winners, valid, invalid = run_simulation(conn, args.year)
    conn.close()

    if not winners:
        print("No results to process")
        return

    # Step 3: Generate shapefile
    if not args.no_map:
        print("\n" + "=" * 60)
        print("Step 3: Generating output shapefile")
        print("=" * 60)
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        output_path = os.path.join(OUTPUT_DIR, f"mapa{args.year}")
        generate_shapefile(TEMPLATE_SHP, output_path, winners, valid, invalid)
        print(f"Shapefile saved to {output_path}.shp")

        # Step 4: Render map
        if not args.skip_map:
            print("\n" + "=" * 60)
            print("Step 4: Rendering election map")
            print("=" * 60)
            img_path = os.path.join(OUTPUT_DIR, f"mapa{args.year}.png")
            render_map(
                f"{output_path}.shp",
                img_path,
                width=args.width,
                height=args.height
            )

    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == "__main__":
    main()
