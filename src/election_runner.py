"""Election simulation runner.

Runs the FPTP simulation for a given year, processing all regions
and generating the output shapefile.
"""

import collections
import os
import sqlite3


def find_party_file(region_path, year):
    """Find the party file for a region and year.

    Checks region-specific files first, then falls back to Spain-wide files.
    """
    candidates = [
        os.path.join(region_path, f"partidos{year % 100:02d}.dat"),
        os.path.join(region_path, f"partidos{year}.dat"),
        os.path.join("data", "partidos", f"esp{year % 100:02d}.dat"),
        os.path.join("data", "partidos", f"esp{year}.dat"),
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return None


def get_votes_for_constituency(conn, year, inclusion_codes, exclusion_codes):
    """Query vote totals for a constituency defined by INE code prefixes.

    Returns a dict mapping party -> total votes.
    """
    table = f"resultados{year}"
    votes = collections.Counter()

    for code in inclusion_codes:
        rows = conn.execute(
            f"SELECT candidatura, SUM(votos) FROM {table} "
            f"WHERE mesa LIKE ? GROUP BY candidatura",
            (code + "%",),
        )
        for candidatura, votos in rows:
            votes[candidatura] += votos

    for code in exclusion_codes:
        rows = conn.execute(
            f"SELECT candidatura, SUM(votos) FROM {table} "
            f"WHERE mesa LIKE ? GROUP BY candidatura",
            (code + "%",),
        )
        for candidatura, votos in rows:
            votes[candidatura] -= votos

    return dict(votes)


def run_simulation(conn, year, circ_dir="data/circunscripciones", method="transfer"):
    """Run the FPTP simulation for a given year.

    Args:
        conn: SQLite database connection
        year: Election year
        circ_dir: Directory containing constituency definitions
        method: Simulation method - 'transfer' (two-round with vote transfer) or
                'plurality' (simple FPTP, no transfers)

    Returns (winners, valid, invalid) where:
    - winners: dict mapping constituency_name -> winning party
    - valid: dict mapping province_code -> {constituency_name -> (inclusion_codes)}
    - invalid: dict mapping province_code -> {constituency_name -> (exclusion_codes)}
    """
    from .party_parser import read_party_file
    from .constituency_parser import parse_constituency_file
    from .simulation import simulate_winner, simulate_plurality

    # Get available provinces from database
    table = f"resultados{year}"
    rows = conn.execute(f"SELECT DISTINCT SUBSTR(mesa, 1, 2) FROM {table}").fetchall()
    available_provinces = set(r[0] for r in rows)
    if not available_provinces:
        print(f"[ERROR] No data found in table {table}")
        return {}, {}, {}
    print(f"[INFO] Available provinces in DB: {sorted(available_provinces)}")

    # Process all regions
    regions = sorted([
        d for d in os.listdir(circ_dir)
        if os.path.isdir(os.path.join(circ_dir, d)) and not d.startswith(".")
    ])

    all_winners = {}
    all_valid = {}
    all_invalid = {}
    representatives = collections.Counter()

    for region_name in regions:
        region_path = os.path.join(circ_dir, region_name)
        if not os.path.isdir(region_path):
            print(f"[SKIP] {region_path} not found")
            continue

        # Find party file
        party_file = find_party_file(region_path, year)
        if party_file is None:
            print(f"[SKIP] No party file found for {region_name} year {year}")
            continue

        codes, transfers = read_party_file(party_file)

        # Build valid/invalid lookup for shapefile assignment
        region_valid = {}
        region_invalid = {}
        constituencies = []

        for filename in sorted(os.listdir(region_path)):
            if filename.startswith("partidos") or filename.startswith("."):
                continue
            if not filename.endswith(".dat"):
                continue

            ncirc = filename.replace("circ", "").replace(".dat", "")
            province_code = ncirc[:2] if len(ncirc) >= 2 else ""
            filepath = os.path.join(region_path, filename)
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

            raw_votes = get_votes_for_constituency(conn, year, inclusions, exclusions)

            # Map numeric codes to party names
            party_votes = collections.Counter()
            for candidatura, votos in raw_votes.items():
                party = codes.get(candidatura, "R")
                party_votes[party] += votos

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
