"""Election simulation runner.

Runs the FPTP simulation for a given year, processing all regions
and generating the output shapefile.
"""

import bisect
import collections
import os
from dataclasses import dataclass

from .dat_parser import parse_dat_file
from .party_parser import read_party_file
from .constituency_parser import parse_constituency_file
from .simulation import simulate_winner, simulate_plurality


# Election years and their raw data file paths (relative to project root)
YEARS = {
    "2008": "data/raw/2008/10020803.DAT",
    "2011": "data/raw/2011/10021111.DAT",
    "2015": "data/raw/2015/10021215.DAT",
    "2016": "data/raw/2016/10021606.DAT",
    "2019a": "data/raw/2019a/10021904.DAT",
    "2019b": "data/raw/2019b/10021911.DAT",
}


@dataclass
class YearData:
    """Preprocessed vote data for a single election year.

    Attributes:
        raw: dict mapping mesa -> {candidatura: votos}.
        sorted_mesas: list of all mesa codes, sorted lexicographically.
    """

    raw: dict
    sorted_mesas: list


def load_region_map(regions_path="data/regions.dat"):
    """Load the province-to-region mapping.

    Returns dict mapping province_code (str) -> region_name (str).
    """
    mapping = {}
    with open(regions_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) >= 2:
                mapping[parts[0]] = parts[1]
    return mapping


def find_party_file(region_name, year):
    """Find the party file for a region and year.

    Looks in data/partidos/{year}/{region}.yaml
    Falls back to data/partidos/{year}/esp.yaml if not found.
    """
    partidos_dir = os.path.join("data", "partidos")
    year_dir = os.path.join(partidos_dir, str(year))
    candidates = [
        os.path.join(year_dir, f"{region_name}.yaml"),
        os.path.join(year_dir, "esp.yaml"),
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return None


def load_year_data(year):
    """Load all vote data for a year into memory from the raw DAT file.

    Returns a YearData object with raw mesa-level data and a sorted list
    of all mesa codes for fast prefix-based queries.
    """
    path = YEARS.get(year)
    if not path or not os.path.exists(path):
        return YearData(raw={}, sorted_mesas=[])
    data = {}
    for mesa, candidatura, votos in parse_dat_file(path):
        if mesa not in data:
            data[mesa] = {}
        cand_int = int(candidatura)
        data[mesa][cand_int] = data[mesa].get(cand_int, 0) + votos

    sorted_mesas = sorted(data.keys())
    return YearData(raw=data, sorted_mesas=sorted_mesas)


def _mesas_for_prefix(sorted_mesas, prefix):
    """Return the slice of sorted mesa codes that start with prefix."""
    lo = bisect.bisect_left(sorted_mesas, prefix)
    hi = bisect.bisect_right(sorted_mesas, prefix + "~")
    return sorted_mesas[lo:hi]


def get_votes_for_constituency(year_data, inclusion_codes, exclusion_codes):
    """Compute vote totals for a constituency from preloaded data.

    Returns a dict mapping party -> total votes.
    """
    votes = collections.Counter()
    sorted_mesas = year_data.sorted_mesas

    # Build sets of mesas matching inclusion/exclusion prefixes.
    included = set()
    for code in inclusion_codes:
        included.update(_mesas_for_prefix(sorted_mesas, code))

    excluded = set()
    for code in exclusion_codes:
        excluded.update(_mesas_for_prefix(sorted_mesas, code))

    add_mesas = included - excluded
    sub_mesas = excluded - included

    for mesa in add_mesas:
        for candidatura, votos in year_data.raw[mesa].items():
            votes[candidatura] += votos
    for mesa in sub_mesas:
        for candidatura, votos in year_data.raw[mesa].items():
            votes[candidatura] -= votos

    return dict(votes)


def run_simulation(year, circ_dir="data/circunscripciones", method="transfer"):
    """Run the FPTP simulation for a given year.

    Args:
        year: Election year
        circ_dir: Directory containing province constituency definitions (flat)
        method: Simulation method - 'transfer' (two-round with vote transfer) or
                'plurality' (simple FPTP, no transfers)

    Returns (winners, valid, invalid) where:
    - winners: dict mapping constituency_name -> winning party
    - valid: dict mapping province_code -> {constituency_name -> (inclusion_codes)}
    - invalid: dict mapping province_code -> {constituency_name -> (exclusion_codes)}
    """
    # Load province -> region mapping
    region_map = load_region_map()

    # Load vote data for the year from raw DAT file
    year_data = load_year_data(year)
    if not year_data:
        print(f"[ERROR] No data found for year {year}")
        return {}, {}, {}

    # Get available provinces from loaded data
    available_provinces = set(mesa[:2] for mesa in year_data.raw)
    print(f"[INFO] Available provinces: {sorted(available_provinces)}")

    # Group province files by region (so each party file is loaded once)
    region_provinces = collections.defaultdict(list)  # region_name -> [province_code, ...]
    province_files = {}  # province_code -> filepath

    for filename in sorted(os.listdir(circ_dir)):
        if not filename.startswith("circ") or not filename.endswith(".dat"):
            continue
        if filename.startswith("partidos"):
            continue

        ncirc = filename.replace("circ", "").replace(".dat", "")
        province_code = ncirc[:2] if len(ncirc) >= 2 else ""
        if not province_code:
            continue

        filepath = os.path.join(circ_dir, filename)
        province_files[province_code] = filepath

        region_name = region_map.get(province_code, "esp")
        region_provinces[region_name].append(province_code)

    all_winners = {}
    all_valid = {}
    all_invalid = {}
    representatives = collections.Counter()

    # Process each region (grouped by party file)
    for region_name in sorted(region_provinces.keys()):
        provinces = region_provinces[region_name]

        # Find party file
        party_file = find_party_file(region_name, year)
        if party_file is None:
            print(f"[SKIP] No party file found for {region_name} year {year}")
            continue

        codes, transfers = read_party_file(party_file)

        # Build valid/invalid lookup for shapefile assignment
        region_valid = {}
        region_invalid = {}
        constituencies = []

        for province_code in sorted(provinces):
            filepath = province_files[province_code]
            file_constituencies = parse_constituency_file(filepath)

            if province_code not in region_valid:
                region_valid[province_code] = {}
                region_invalid[province_code] = {}

            for name, inclusions, exclusions in file_constituencies:
                region_valid[province_code][name] = tuple(inclusions)
                region_invalid[province_code][name] = tuple(exclusions)

            # Check if this province has data
            if province_code in available_provinces:
                constituencies.extend(file_constituencies)

        if not constituencies:
            continue

        print(f"[INFO] Region {region_name}: party file = {party_file}")

        # Process constituencies
        for name, inclusions, exclusions in constituencies:
            if inclusions:
                prov = inclusions[0][:2]
            else:
                prov = ""

            if prov not in available_provinces:
                continue

            raw_votes = get_votes_for_constituency(year_data, inclusions, exclusions)

            # Map numeric codes to party names
            party_votes = collections.Counter()
            unmapped_votes = collections.Counter()
            for candidatura, votos in raw_votes.items():
                party = codes.get(candidatura, "R")
                party_votes[party] += votos
                if party == "R":
                    unmapped_votes[candidatura] += votos

            total_votes = sum(party_votes.values())
            r_votes = party_votes.get("R", 0)
            if total_votes > 0 and r_votes / total_votes > 0.05:
                top_unmapped = unmapped_votes.most_common(3)
                codes_str = ", ".join(f"{c:06d}={v:,}" for c, v in top_unmapped)
                print(f"  [WARN] {name}: R={r_votes:,} ({r_votes/total_votes:.0%}) "
                      f"of {total_votes:,} total | top codes: {codes_str}")

            if not party_votes:
                all_winners[name] = "R"
                continue

            if method == "plurality":
                winner = simulate_plurality(dict(party_votes))
            else:
                winner = simulate_winner(dict(party_votes), transfers)
            all_winners[name] = winner
            representatives[winner] += 1
            print(f"  {name}: {winner}")

        # Merge region valid/invalid into all_valid/all_invalid
        for prov, v in region_valid.items():
            if prov not in all_valid:
                all_valid[prov] = {}
            all_valid[prov].update(v)
        for prov, inv in region_invalid.items():
            if prov not in all_invalid:
                all_invalid[prov] = {}
            all_invalid[prov].update(inv)

    print(f"\n=== Representatives by party ===")
    for party, count in representatives.most_common():
        print(f"  {party}: {count}")

    return all_winners, all_valid, all_invalid
