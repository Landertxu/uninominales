# AGENTS.md — uninominales

Spanish election simulator (FPTP/uninominales) using INE DAT files. Python 3, no database — all data parsed in-memory.

## CRITICAL RULES

1. **NEVER commit or push without explicit user approval.** Always ask "Ready to commit?" or similar before running `git commit` or `git push`. The user wants to review changes first.

## Run commands

```bash
# Always run from uninominales/
python3 run.py                                  # Default: configs/default.yaml (2015)
python3 run.py --config configs/2016.yaml       # Use a per-year config
python3 run.py --config configs/2019a.yaml      # April 2019 election
python3 run.py --config configs/2019b.yaml      # November 2019 election
python3 run.py --year 2019a                     # Shorthand (loads configs/2019a.yaml)
```

**Important:** `--year` is a string. 2019 has two elections: `2019a` (April) and `2019b` (November). Single-election years: `2008`, `2011`, `2015`, `2016`.

## Testing

```bash
# Fast tests (unit + regression)
pytest

# Slow tests (golden PNG comparison, ~2 min)
pytest --runslow

# Regenerate golden images after intentional changes
pytest --regenerate-golden
```

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

- `configs/*.yaml` — Per-year run configurations and default config
- `data/raw/YYYY/*.DAT` — INE election data (large files, ~25 MB each)
- `data/geographic/spainYYYY/geographic/` — Census-section shapefile
- `data/geographic/spainYYYY/holes/` — Hole-filler assignments for this census
- `data/geographic/spainYYYY/constituencies/` — Base province constituency definitions (for census years)
- `data/geographic/spainYYYY/deltas/` — Constituency override files vs the base census year
- `data/partidos/colors/YYYY.yaml` — Per-election party colors
- `data/partidos/YYYY/config.yaml` — Per-year party configuration, references a census
- `data/partidos/YYYY/{region}.yaml` — Per-year, per-region party codes and transfer rules
- `data/regions.dat` — Province code → region name mapping

## Adding a new election year

1. Place the INE DAT file in `data/raw/YYYY/`
2. Create `data/partidos/YYYY/` with:
   - `config.yaml` referencing the census dataset (e.g. `census_dir: data/census/spain2011`)
   - per-region YAML files (`and.yaml`, `esp.yaml`, etc.)
3. Create `configs/YYYY.yaml` pointing to:
   - the DAT file and party directory
   - the election-specific `geographic_dir`
   - the `base_constituencies_dir` (usually a census year like `data/geographic/spain2011/constituencies`)
4. If the election's constituency boundaries differ from the base, add override files in `data/geographic/{geographic_dir}/deltas/`
5. Run `python3 run.py --config configs/YYYY.yaml` and check for `[WARN] R=XX%` lines (>5% R is suspicious)

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

## Gotchas

- Province code = first 2 digits of mesa (census section) code
- The template shapefile (`data/geographic/spain2011/geographic/SECC_CPV_E_20111101_01_R_INE`) has `.prj` copied to output by shapefile_gen.py
- Party code mappings vary by region — a code in Madrid may not exist in Galicia
- Transfer fractions should sum to ≤1.0 (unallocated fraction stays with the eliminated party as "lost")
- `geographic_dir` is required when `map` is not `none`
