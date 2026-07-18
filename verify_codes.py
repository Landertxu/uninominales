#!/usr/bin/env python3
"""Verify party code coverage: every code mapping should match the 5% threshold rule."""

import yaml
import os
import sys
from collections import defaultdict
from src.election_runner import load_year_data, load_region_map, get_votes_for_constituency, find_party_file
from src.party_parser import read_party_file
from src.constituency_parser import parse_constituency_file

THRESHOLD = 5.0  # percent


def get_votes_by_region(year):
    """For each region, return {code: {constituency: pct}} for codes above 0."""
    region_map = load_region_map()
    year_data = load_year_data(year)
    if not year_data:
        return {}

    circ_dir = "data/circunscripciones"
    # region -> code -> {constituency_name: pct}
    region_code_pcts = defaultdict(lambda: defaultdict(dict))

    for filename in sorted(os.listdir(circ_dir)):
        if not filename.startswith("circ") or not filename.endswith(".dat"):
            continue
        ncirc = filename.replace("circ", "").replace(".dat", "")
        prov = ncirc[:2]
        region = region_map.get(prov, "esp")

        filepath = os.path.join(circ_dir, filename)
        constituencies = parse_constituency_file(filepath)

        for name, inclusions, exclusions in constituencies:
            raw = get_votes_for_constituency(year_data, inclusions, exclusions)
            total = sum(raw.values())
            if total == 0:
                continue
            for code, votes in raw.items():
                pct = votes / total * 100
                region_code_pcts[region][code][name] = pct

    return region_code_pcts


def load_yaml_codes(year):
    """Load all code->party mappings from YAML files for a year. Returns {region: {code: party}}."""
    partidos_dir = f"data/partidos/{year}"
    if not os.path.exists(partidos_dir):
        return {}

    result = {}
    for filename in sorted(os.listdir(partidos_dir)):
        if not filename.endswith(".yaml"):
            continue
        region = filename.replace(".yaml", "")
        yaml_path = os.path.join(partidos_dir, filename)
        codes, _ = read_party_file(yaml_path)
        result[region] = codes  # {int_code: party_name}
    return result


def verify_year(year):
    """Check YAML codes against actual vote data for a year."""
    region_data = get_votes_by_region(year)
    yaml_codes = load_yaml_codes(year)

    all_regions = set(region_data.keys()) | set(yaml_codes.keys())
    issues = []

    for region in sorted(all_regions):
        code_pcts = region_data.get(region, {})
        y_codes = yaml_codes.get(region, {})

        # Build {code: party} from YAML
        yaml_by_code = y_codes  # {int_code: party_name}

        # For each code that appears in raw data, check the 5% rule
        all_codes = set(code_pcts.keys()) | set(yaml_by_code.keys())

        for code in sorted(all_codes):
            max_pct = 0
            max_circ = ""
            if code in code_pcts:
                for circ, pct in code_pcts[code].items():
                    if pct > max_pct:
                        max_pct = pct
                        max_circ = circ

            in_yaml = code in yaml_by_code
            above_threshold = max_pct >= THRESHOLD

            party_name = yaml_by_code.get(code, "?")

            if above_threshold and not in_yaml:
                issues.append(f"  MISSING: {region} code {code} ({party_name}) reaches {max_pct:.1f}% in {max_circ} but not in YAML")
            elif not above_threshold and in_yaml and max_pct > 0:
                issues.append(f"  REMOVE:  {region} code {code} ({party_name}) max {max_pct:.1f}% in {max_circ} — below {THRESHOLD}% threshold")
            elif not above_threshold and in_yaml and max_pct == 0:
                issues.append(f"  UNUSED:  {region} code {code} ({party_name}) has 0 votes everywhere")

    return issues


def main():
    years = sys.argv[1:] if len(sys.argv) > 1 else ["2008", "2011", "2015", "2016", "2019a", "2019b"]
    total_issues = 0

    for year in years:
        print(f"\n{'='*60}")
        print(f"  {year}")
        print(f"{'='*60}")
        issues = verify_year(year)
        if issues:
            for issue in issues:
                print(issue)
            total_issues += len(issues)
        else:
            print("  OK — all codes consistent")

    print(f"\n{'='*60}")
    print(f"  TOTAL: {total_issues} issues")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
