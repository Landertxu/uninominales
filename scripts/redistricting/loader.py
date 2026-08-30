"""Load constituency divisions and census population data."""

import csv
import os
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.constituency_parser import parse_constituency_file


def load_population(path):
    """Load population data from a CSV with columns seccion_censal,population.

    Returns dict mapping section code -> population.
    """
    population = {}
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            section = row["seccion_censal"].strip()
            population[section] = int(row["population"])
    return population


def load_division(constituencies_dir):
    """Load all constituency definition files from a directory.

    Returns dict mapping province_code -> [(constituency_name, inclusions, exclusions), ...].
    """
    division = defaultdict(list)
    for filename in sorted(os.listdir(constituencies_dir)):
        if not filename.startswith("circ") or not filename.endswith(".dat"):
            continue

        ncirc = filename.replace("circ", "").replace(".dat", "")
        province_code = ncirc[:2] if len(ncirc) >= 2 else ""
        if not province_code:
            continue

        filepath = os.path.join(constituencies_dir, filename)
        division[province_code].extend(parse_constituency_file(filepath))

    return dict(division)


def assign_sections(constituencies, population):
    """Assign each census section to its constituency based on prefix rules.

    Returns dict mapping section code -> constituency name.
    """
    assignment = {}

    for section in population:
        for name, inclusions, exclusions in constituencies:
            included = any(section.startswith(prefix) for prefix in inclusions)
            excluded = any(section.startswith(prefix) for prefix in exclusions)
            if included and not excluded:
                assignment[section] = name
                break

    return assignment


def section_to_municipality(section):
    """Return the municipality code (5 digits) for a census section."""
    return section[:5]


def section_to_district(section):
    """Return the census district code (7 digits) for a census section."""
    return section[:7]
