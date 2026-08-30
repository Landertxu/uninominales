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
from dataclasses import dataclass
from pathlib import Path

import yaml

from src.election_runner import run_simulation
from src.shapefile_gen import generate_shapefile
from src.visualization import render_map

PROJECT_ROOT = Path(__file__).parent
OUTPUT_DIR = "output"
DEFAULT_CONFIG = "configs/default.yaml"


@dataclass
class WorkflowPaths:
    """Resolved paths for a workflow run."""

    output_prefix: str
    votes_file: str
    partidos_dir: str
    geographic_dir: str
    map_template: str
    holes_dir: str
    base_circ_dir: str
    delta_circ_dir: str
    regions_path: str
    colors_dir: str


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

    Returns (map_template, holes_dir, delta_circ_dir).
    Auto-detects .shp file in {geographic_dir}/geographic/
    """
    geographic_subdir = os.path.join(geographic_dir, "geographic")
    holes_dir = os.path.join(geographic_dir, "holes")
    delta_circ_dir = os.path.join(geographic_dir, "deltas")

    # Auto-detect .shp file
    map_template = None
    if os.path.isdir(geographic_subdir):
        for fname in os.listdir(geographic_subdir):
            if fname.endswith(".shp"):
                # Remove .shp extension to get the template path
                map_template = os.path.join(geographic_subdir, fname[:-4])
                break

    return map_template, holes_dir, delta_circ_dir


def build_args():
    """Build the final configuration from defaults and config file."""
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
    cli_args = parser.parse_args()

    # Determine which config file to load
    if cli_args.config:
        config_path = cli_args.config
    elif cli_args.year:
        config_path = f"configs/{cli_args.year}.yaml"
    else:
        config_path = DEFAULT_CONFIG

    return load_config(config_path)


def resolve_paths(config):
    """Resolve all paths relative to PROJECT_ROOT.

    Returns a WorkflowPaths object or raises SystemExit on missing required paths.
    """
    year = config["year"]

    output_prefix = config.get("output") or os.path.join(OUTPUT_DIR, f"mapa{year}")
    output_prefix = str(PROJECT_ROOT / output_prefix)

    partidos_dir = config.get("partidos_dir")
    if not partidos_dir:
        print("Error: --partidos-dir is required (or set in config file).")
        raise SystemExit(1)
    partidos_dir = str(PROJECT_ROOT / partidos_dir)

    geographic_dir = config.get("geographic_dir")
    if not geographic_dir:
        print("Error: --geographic-dir is required (or set in config file).")
        raise SystemExit(1)
    geographic_dir = str(PROJECT_ROOT / geographic_dir)

    votes_file = config.get("votes_file")
    if not votes_file:
        print("Error: --votes-file is required (or set in config file).")
        raise SystemExit(1)
    votes_file = str(PROJECT_ROOT / votes_file)

    base_circ_dir = config.get("base_constituencies_dir")
    if not base_circ_dir:
        print("Error: base_constituencies_dir is required (or set in config file).")
        raise SystemExit(1)
    base_circ_dir = str(PROJECT_ROOT / base_circ_dir)

    map_template, holes_dir, delta_circ_dir = derive_geographic_paths(geographic_dir)

    return WorkflowPaths(
        output_prefix=output_prefix,
        votes_file=votes_file,
        partidos_dir=partidos_dir,
        geographic_dir=geographic_dir,
        map_template=map_template,
        holes_dir=holes_dir,
        base_circ_dir=base_circ_dir,
        delta_circ_dir=delta_circ_dir,
        regions_path=str(PROJECT_ROOT / "data/regions.dat"),
        colors_dir=str(PROJECT_ROOT / "data/partidos/colors"),
    )


def validate_paths(paths):
    """Check that required directories and shapefiles exist."""
    if not os.path.isdir(paths.partidos_dir):
        print(f"Error: partidos directory not found: {paths.partidos_dir}")
        raise SystemExit(1)

    if not os.path.isdir(paths.geographic_dir):
        print(f"Error: geographic directory not found: {paths.geographic_dir}")
        raise SystemExit(1)

    if not os.path.isdir(paths.base_circ_dir):
        print(f"Error: base constituencies directory not found: {paths.base_circ_dir}")
        raise SystemExit(1)

    if not paths.map_template:
        print(f"Error: no .shp file found in {paths.geographic_dir}/geographic/")
        raise SystemExit(1)


def run_viz_only(paths, year, config):
    """Render the map from an existing shapefile."""
    shp_path = f"{paths.output_prefix}.shp"
    if not os.path.exists(shp_path):
        print(f"Error: {shp_path} not found. Run full workflow first.")
        raise SystemExit(1)

    img_path = f"{paths.output_prefix}.png"
    render_map(
        shp_path,
        img_path,
        election=year,
        colors_dir=paths.colors_dir,
        width=config.get("width", 1100),
        height=config.get("height", 900),
    )


def run_simulation_step(paths, year, method):
    """Run the election simulation."""
    print("=" * 60)
    print(f"Step 1: Running {method} simulation for {year}")
    print("=" * 60)
    return run_simulation(
        votes_file=paths.votes_file,
        partidos_dir=paths.partidos_dir,
        base_circ_dir=paths.base_circ_dir,
        delta_circ_dir=paths.delta_circ_dir,
        regions_path=paths.regions_path,
        method=method,
    )


def generate_output_files(paths, winners, valid, invalid, year, config):
    """Generate output shapefile and PNG map."""
    map_mode = config.get("map", "png")

    if map_mode not in ("shapefile", "png"):
        return

    print("\n" + "=" * 60)
    print("Step 2: Generating output shapefile")
    print("=" * 60)
    os.makedirs(os.path.dirname(paths.output_prefix) or OUTPUT_DIR, exist_ok=True)
    generate_shapefile(
        paths.map_template,
        paths.output_prefix,
        winners,
        valid,
        invalid,
        holes_dir=paths.holes_dir,
    )
    print(f"Shapefile saved to {paths.output_prefix}.shp")

    if map_mode == "png":
        print("\n" + "=" * 60)
        print("Step 3: Rendering election map")
        print("=" * 60)
        img_path = f"{paths.output_prefix}.png"
        render_map(
            f"{paths.output_prefix}.shp",
            img_path,
            election=year,
            colors_dir=paths.colors_dir,
            width=config.get("width", 1100),
            height=config.get("height", 900),
        )


def main():
    config = build_args()

    year = config.get("year")
    if not year:
        print("Error: --year is required (or set in config file).")
        raise SystemExit(1)

    paths = resolve_paths(config)
    validate_paths(paths)

    if config.get("viz_only"):
        run_viz_only(paths, year, config)
    else:
        winners, valid, invalid = run_simulation_step(paths, year, config.get("method", "transfer"))
        if not winners:
            print("No results to process")
            return
        generate_output_files(paths, winners, valid, invalid, year, config)

    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == "__main__":
    main()
