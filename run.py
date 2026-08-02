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


def load_config(path):
    """Load a YAML config file. Returns an empty dict if the file is missing."""
    if not path or not os.path.exists(path):
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def load_party_config(partidos_dir):
    """Load the per-year party configuration.

    Returns a dict. Currently supports:
      - census_dir: path to the census dataset used by this party configuration
    """
    config_path = os.path.join(partidos_dir, "config.yaml")
    return load_config(config_path)


def derive_geographic_paths(geographic_dir):
    """Derive geographic-related paths from the geographic directory.

    Returns (map_template, holes_dir, circ_dir).
    Auto-detects .shp file in {geographic_dir}/geographic/
    """
    geographic_subdir = os.path.join(geographic_dir, "geographic")
    holes_dir = os.path.join(geographic_dir, "holes")
    circ_dir = os.path.join(geographic_dir, "constituencies")

    # Auto-detect .shp file
    map_template = None
    if os.path.isdir(geographic_subdir):
        for fname in os.listdir(geographic_subdir):
            if fname.endswith(".shp"):
                # Remove .shp extension to get the template path
                map_template = os.path.join(geographic_subdir, fname[:-4])
                break

    return map_template, holes_dir, circ_dir


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
        "--geographic-dir", type=str,
        help="Directory containing geographic data (shapefile and holes)"
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
        "--holes-dir", type=str,
        help="Directory containing hole-filler assignment files"
    )
    parser.add_argument(
        "--output", type=str,
        help="Output path prefix"
    )
    parser.add_argument(
        "--map", choices=["none", "shapefile", "png"], default="png",
        help="Map generation mode: none (no map), shapefile (shapefile only), png (full map with PNG)"
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

    # Determine which config file to load
    config = {}
    if cli_args.config:
        # Explicit config file specified
        config_path = cli_args.config
        if os.path.exists(config_path):
            config = load_config(config_path)
    elif cli_args.year:
        # Year specified, try to load year-specific config
        config_path = f"configs/{cli_args.year}.yaml"
        if os.path.exists(config_path):
            config = load_config(config_path)
    else:
        # No year or config specified, use default
        config_path = DEFAULT_CONFIG
        if os.path.exists(config_path):
            config = load_config(config_path)

    # Simple CLI overrides: if a flag was given, use it.
    for key in ["year", "votes_file", "partidos_dir", "geographic_dir", "circ_dir",
                "map_template", "holes_dir", "output", "method", "width", "height"]:
        value = getattr(cli_args, key)
        if value is not None:
            config[key] = value

    # Handle --map flag
    if cli_args.map != "png":  # png is the default
        config["map"] = cli_args.map

    # Boolean flags: CLI overrides config.
    if cli_args.viz_only:
        config["viz_only"] = True

    return config


def main():
    config = build_args()

    # Change to script directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    year = config.get("year")
    if not year:
        print("Error: --year is required (or set in config file).")
        return

    output_prefix = config.get("output") or os.path.join(OUTPUT_DIR, f"mapa{year}")

    partidos_dir = config.get("partidos_dir")
    if not partidos_dir:
        print("Error: --partidos-dir is required (or set in config file).")
        return

    if not os.path.isdir(partidos_dir):
        print(f"Error: partidos directory not found: {partidos_dir}")
        return

    # Get map mode
    map_mode = config.get("map", "png")

    # Derive geographic paths
    geographic_dir = config.get("geographic_dir")
    if not geographic_dir:
        print("Error: --geographic-dir is required (or set in config file).")
        return

    if not os.path.isdir(geographic_dir):
        print(f"Error: geographic directory not found: {geographic_dir}")
        return

    default_map_template, default_holes_dir, default_circ_dir = derive_geographic_paths(geographic_dir)

    # Validate that we found a shapefile
    if not default_map_template:
        print(f"Error: no .shp file found in {geographic_dir}/geographic/")
        return

    map_template = config.get("map_template") or default_map_template
    holes_dir = config.get("holes_dir") or default_holes_dir
    circ_dir = config.get("circ_dir") or default_circ_dir

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
            election=year,
            width=config.get("width", 1100),
            height=config.get("height", 900),
        )
        return

    votes_file = config.get("votes_file")
    if not votes_file:
        print("Error: --votes-file is required (or set in config file).")
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
    if map_mode in ["shapefile", "png"]:
        print("\n" + "=" * 60)
        print("Step 2: Generating output shapefile")
        print("=" * 60)
        os.makedirs(os.path.dirname(output_prefix) or OUTPUT_DIR, exist_ok=True)
        generate_shapefile(
            map_template,
            output_prefix,
            winners,
            valid,
            invalid,
            holes_dir=holes_dir,
        )
        print(f"Shapefile saved to {output_prefix}.shp")

        # Step 3: Render map
        if map_mode == "png":
            print("\n" + "=" * 60)
            print("Step 3: Rendering election map")
            print("=" * 60)
            img_path = f"{output_prefix}.png"
            render_map(
                f"{output_prefix}.shp",
                img_path,
                election=year,
                width=config.get("width", 1100),
                height=config.get("height", 900),
            )

    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == "__main__":
    main()
