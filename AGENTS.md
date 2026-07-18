# AGENTS.md — uninominales_v3

Spanish election simulator (FPTP/uninominales) using INE DAT files. Python 3, no database — all data parsed in-memory.

## Run commands

```bash
# Always run from uninominales_v3/
python3 run.py                          # Default: 2015, transfer method
python3 run.py --year 2016              # Specify year (string, not int)
python3 run.py --year 2019a             # April 2019 election
python3 run.py --year 2019b             # November 2019 election
python3 run.py --method plurality       # Simple FPTP without vote transfers
python3 run.py --viz-only               # Re-render map from existing shapefile
python3 run.py --skip-map               # Generate shapefile but skip PNG
python3 run.py --no-map                 # Print results only
```

**Important:** `--year` is a string. 2019 has two elections: `2019a` (April) and `2019b` (November). Single-election years: `2008`, `2011`, `2015`, `2016`.

## No test suite

There are no tests. Verify changes by running the full pipeline and comparing output (seat counts, map visuals). The original project's outputs in `output/` serve as reference.

## Key architecture

- `run.py` — CLI entry point, orchestrates the 3-step pipeline
- `src/dat_parser.py` — Parses INE fixed-width DAT files (36 chars/line, fields at exact offsets)
- `src/election_runner.py` — Loads all data for a year, runs simulation per constituency, prints results
- `src/simulation.py` — `simulate_winner()` (vote transfer) and `simulate_plurality()` (simple FPTP)
- `src/party_parser.py` — Reads YAML party files (codes + transfer rules)
- `src/constituency_parser.py` — Reads circXX.dat files (inclusion/exclusion prefix matching)
- `src/shapefile_gen.py` — Adds CIRC and PARTIDO columns to template shapefile
- `src/visualization/` — Renders PNG map with Canary Islands relocation and Madrid/Barcelona insets

## Data layout

- `data/raw/YYYY/*.DAT` — INE election data (large files, ~25 MB each)
- `data/circunscripciones/circXX.dat` — 52 province constituency definitions
- `data/partidos/parties.yaml` — Central party metadata (names, colors)
- `data/partidos/YYYY/{region}.yaml` — Per-year, per-region party codes and transfer rules
- `data/regions.dat` — Province code → region name mapping
- `data/mapas/molde/` — Template census-section shapefile

## Party YAML format

```yaml
# data/partidos/YYYY/{region}.yaml
parties:
  PP: [83, 84, 85, 86]       # List of candidatura codes for this party
  PSOE: [94]
transfers:
  PP: {C's: 0.3, VOX: 0.2}   # When PP is eliminated, 30% goes to C's, 20% to VOX
  R: {PP: 0.3, PSOE: 0.4}    # Resto redistribution (always eliminated)
```

Codes are 2-3 digit integers from the INE data. Party codes vary by region and year — check `data/partidos/YYYY/{region}.yaml` for the correct mapping.

## R-handling divergence from original

The `R` (resto) party is **always eliminated** and redistributed. The original algorithm could protect R from elimination if it earned ≥20% of a district's votes. This v3 change is intentional — R is an artificial catch-all for minor/unknown candidaturas and should never win a seat. On historical data (2008–2016) this never triggers. For 2019, it flips one seat: **Navarra4** (April 2019).

## Adding a new election year

1. Place the INE DAT file in `data/raw/YYYY/`
2. Add the year to `YEARS` dict in `src/election_runner.py`
3. Create `data/partidos/YYYY/` with per-region YAML files
4. Verify party codes against the INE candidatura file for that year
5. Run `python3 run.py --year YYYY` and check for `[WARN] R=XX%` lines (>5% R is suspicious)

## Gotchas

- `run.py` does `os.chdir()` to its own directory — all paths are relative to project root
- Province code = first 2 digits of mesa (census section) code
- The template shapefile (`data/mapas/molde/SECC_CPV_E_20111101_01_R_INE`) has `.prj` copied to output by shapefile_gen.py
- Party code mappings vary by region — a code in Madrid may not exist in Galicia
- Transfer fractions should sum to ≤1.0 (unallocated fraction stays with the eliminated party as "lost")
