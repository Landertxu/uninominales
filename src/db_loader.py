"""SQLite database loader for election data.

Loads parsed INE DAT file data into the SQLite database.
"""

import os
import sqlite3

from .dat_parser import parse_dat_file


# Election years and their raw data file paths (relative to project root)
YEARS = {
    2008: "data/raw/2008/10020803.DAT",
    2011: "data/raw/2011/10021111.DAT",
    2015: "data/raw/2015/10021215.DAT",
}


def create_tables(conn):
    """Create results tables for each election year."""
    for year in YEARS:
        table = f"resultados{year}"
        conn.execute(f"DROP TABLE IF EXISTS {table}")
        conn.execute(
            f"CREATE TABLE {table} "
            "(mesa TEXT, candidatura INTEGER, votos INTEGER)"
        )


def load_year(conn, year, filepath):
    """Load data for one election year into the database.

    Returns (raw_count, agg_count) tuple.
    """
    table = f"resultados{year}"
    rows = []
    for mesa, candidatura, votos in parse_dat_file(filepath):
        rows.append((mesa, int(candidatura), votos))

    conn.executemany(f"INSERT INTO {table} VALUES (?, ?, ?)", rows)
    conn.commit()
    return len(rows), len(rows)


def load_all_data(db_path="elecciones.db"):
    """Load all available election data into the database.

    Returns the database connection.
    """
    # Change to project root directory
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    conn = sqlite3.connect(db_path)
    create_tables(conn)

    for year, path in sorted(YEARS.items()):
        if not os.path.exists(path):
            print(f"[SKIP] {path} not found")
            continue
        raw_count, agg_count = load_year(conn, year, path)
        print(f"[OK] {year}: {raw_count} rows loaded from {path}")

    print(f"\nDatabase written to {db_path}")
    return conn
