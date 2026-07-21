#!/usr/bin/env python3
"""Election simulator orchestrator.

Runs the complete workflow:
1. Parse INE DAT file for the election
2. Run FPTP simulation
3. Generate output shapefile
4. Render the election map

Usage:
    python run.py                           # Use configs/default.yaml
    python run.py --config configs/2019a.yaml # Use a custom config file
    python run.py --votes-file ... --partidos-dir ... --year 2019a
    python run.py --viz-only --config configs/2019a.yaml
"""

import argparse
import os

import yaml

from src.election_runner import run_simulation
from src.shapefile_gen import generate_shapefile
from src.visualization import render_map

OUTPUT_DIR = "output"
DEFAULT_CONFIG = "configs/default.yaml"
TEMPLATE_SHP = "data/mapas/molde/SECC_CPV_E_20111101_01_R_INE"
CIRC_INDEX = "data/circunscripciones/index.yaml"
DEFAULT_CIRC_DIR = "data/circunscripciones/census2011"


def load_config(path):
    """Load a YAML config file. Returns an empty dict if the file is missing."""
    if not path or not os.path.exists(path):
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def pick_circ_dir(_year):
    """Auto-pick a constituency division directory.

    TODO: revisit when more than one division exists. For now, default to the
    existing 2011 census division.
    """
    if os.path.exists(DEFAULT_CIRC_DIR):
        return DEFAULT_CIRC_DIR
    # Fallback: if the index file exists, use the first listed division.
    if os.path.exists(CIRC_INDEX):
        with open(CIRC_INDEX) as f:
            data = yaml.safe_load(f) or {}
        if data:
            first = next(iter(data.keys()))
            return os.path.join("data/circunscripciones", first)
    return None


def build_args():
    """Build the final configuration from defaults, config file, and CLI flags."""
    parser = argparse.ArgumentParser(
        description="Election simulator - FPTP system"
    )
    parser.add_argument(
        "--config", type=str,
        help="Path to a YAML config file"
    )
    parser.add_argument(
        "--year", type=str,
        help="Election label, e.g. 2008, 2011, 2015, 2016, 2019a, 2019b"
    )
    parser.add_argument(
        "--votes-file", type=str,
        help="Path to the INE type-10 DAT file"
    )
    parser.add_argument(
        "--partidos-dir", type=str,
        help="Directory containing per-year party YAML files"
    )
    parser.add_argument(
        "--circ-dir", type=str,
        help="Directory containing constituency definition files"
    )
    parser.add_argument(
        "--map-template", type=str,
        help="Path prefix to the template shapefile"
    )
    parser.add_argument(
        "--output", type=str,
        help="Output path prefix"
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
        help="Just render the map from an existing shapefile"
    )
    parser.add_argument(
        "--width", type=int,
        help="Map image width"
    )
    parser.add_argument(
        "--height", type=int,
        help="Map image height"
    )
    parser.add_argument(
        "--method", choices=["transfer", "plurality"],
        help="Simulation method: transfer or plurality"
    )
    cli_args = parser.parse_args()

    # Start with defaults, then config file, then CLI overrides.
    config = {}
    config_path = cli_args.config or DEFAULT_CONFIG
    if config_path and os.path.exists(config_path):
        config = load_config(config_path)

    # Simple CLI overrides: if a flag was given, use it.
    for key in ["year", "votes_file", "partidos_dir", "circ_dir",
                "map_template", "output", "method", "width", "height"]:
        value = getattr(cli_args, key)
        if value is not None:
            config[key] = value

    # Boolean flags: CLI overrides config.
    for key in ["skip_map", "no_map", "viz_only"]:
        if getattr(cli_args, key):
            config[key] = True

    return config, cli_args


def main():
    config, cli_args = build_args()

    # Change to script directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    year = config.get("year")
    if not year:
        print("Error: --year is required (or set in config file).")
        return

    output_prefix = config.get("output") or os.path.join(OUTPUT_DIR, f"mapa{year}")
    map_template = config.get("map_template") or TEMPLATE_SHP

    # Viz-only mode: just render from existing shapefile
    if config.get("viz_only"):
        shp_path = f"{output_prefix}.shp"
        if not os.path.exists(shp_path):
            print(f"Error: {shp_path} not found. Run full workflow first.")
            return
        img_path = f"{output_prefix}.png"
        render_map(
            shp_path,
            img_path,
            width=config.get("width", 1100),
            height=config.get("height", 900),
        )
        return

    votes_file = config.get("votes_file")
    if not votes_file:
        print("Error: --votes-file is required (or set in config file).")
        return

    partidos_dir = config.get("partidos_dir")
    if not partidos_dir:
        print("Error: --partidos-dir is required (or set in config file).")
        return

    circ_dir = config.get("circ_dir")
    if not circ_dir:
        circ_dir = pick_circ_dir(year)
        if not circ_dir:
            print("Error: no constituency division found and --circ-dir not given.")
            return

    method = config.get("method", "transfer")

    # Step 1: Run simulation
    print("=" * 60)
    print(f"Step 1: Running {method} simulation for {year}")
    print("=" * 60)
    winners, valid, invalid = run_simulation(
        votes_file=votes_file,
        partidos_dir=partidos_dir,
        circ_dir=circ_dir,
        method=method,
    )

    if not winners:
        print("No results to process")
        return

    # Step 2: Generate shapefile
    if not config.get("no_map"):
        print("\n" + "=" * 60)
        print("Step 2: Generating output shapefile")
        print("=" * 60)
        os.makedirs(os.path.dirname(output_prefix) or OUTPUT_DIR, exist_ok=True)
        generate_shapefile(map_template, output_prefix, winners, valid, invalid)
        print(f"Shapefile saved to {output_prefix}.shp")

        # Step 3: Render map
        if not config.get("skip_map"):
            print("\n" + "=" * 60)
            print("Step 3: Rendering election map")
            print("=" * 60)
            img_path = f"{output_prefix}.png"
            render_map(
                f"{output_prefix}.shp",
                img_path,
                width=config.get("width", 1100),
                height=config.get("height", 900),
            )

    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == "__main__":
    main()
