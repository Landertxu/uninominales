# Simulador de Elecciones Generales - Sistema Uninominal Mayoría Simple (UMS)

Simula elecciones generales españolas bajo el sistema de distritos uninominales (first-past-the-post) usando datos oficiales del INE.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run complete workflow (load data + simulate + generate map)
python3 run.py

# Or specify a year
python3 run.py --year 2015
```

## Workflow Options

```bash
# Skip data loading (use existing database)
python3 run.py --skip-load

# Skip map rendering (generate shapefile only)
python3 run.py --skip-map

# Don't generate shapefile (print results only)
python3 run.py --no-map

# Customize map dimensions
python3 run.py --width 1200 --height 1000
```

## Project Structure

```
uninominales_v3/
├── run.py                    # Main orchestrator script
├── src/                      # Source modules
│   ├── __init__.py
│   ├── dat_parser.py         # INE DAT file parser
│   ├── party_parser.py       # Party transfer file parser
│   ├── constituency_parser.py # Constituency definition parser
│   ├── simulation.py         # FPTP vote transfer simulation
│   ├── db_loader.py          # SQLite database loader
│   ├── election_runner.py    # Simulation orchestrator
│   ├── shapefile_gen.py      # Shapefile generator
│   └── visualization.py      # Map renderer
├── data/                     # Input data
│   ├── raw/                  # INE election DAT files
│   ├── circunscripciones/    # Constituency definitions
│   ├── partidos/             # Party transfer files
│   └── mapas/molde/          # Template shapefile
├── output/                   # Generated outputs
├── requirements.txt          # Python dependencies
└── README.md
```

## How It Works

1. **Data Loading** (`src/dat_parser.py` + `src/db_loader.py`)
   - Parses INE fixed-width DAT files (candidatura data per census section)
   - Stores aggregated vote counts in `elecciones.db` (SQLite)

2. **Simulation** (`src/simulation.py` + `src/election_runner.py`)
   - For each constituency defined in `circXX.dat`:
     - Queries the database for all party votes within that district
     - Applies transfer rules: parties absorb votes from eliminated parties
     - The party with the most votes wins the seat
   - Returns winners and constituency mappings

3. **Shapefile Generation** (`src/shapefile_gen.py`)
   - Reads the template census-section shapefile
   - Adds CIRC (constituency) and PARTIDO (winning party) columns
   - Saves to `output/mapa{YEAR}.shp`

4. **Visualization** (`src/visualization.py`)
   - Renders the shapefile to a PNG image
   - Detects constituency borders using unique-color technique
   - Relocates Canary Islands to bottom-left corner
   - Draws party-colored constituencies with legend

## Data Files

- **data/raw/** — INE election DAT files (2008, 2011, 2015)
- **data/circunscripciones/** — 12 region folders with constituency definitions
- **data/partidos/** — Spain-wide party transfer files
- **data/mapas/molde/** — Template census-section shapefile

## INE DAT File Format (36 chars/line)

| Field | Position | Description |
|-------|----------|-------------|
| Process | 0:8 | Election process code |
| INE code | 8:21 | Province(2) + municipality(3) + district(2) + section(3) + mesa(3) |
| Candidatura letter | 22 | Data category (NOT party ID) |
| Numeric code | 23:29 | 6-digit party code mapping to party files |
| Votes | 29:36 | Vote count (7 digits) |

## Output

Results are saved to `output/mapa{YEAR}.shp` with fields:
- All original census-section shapefile fields
- `CIRC` — Constituency name
- `PARTIDO` — Winning party abbreviation

The map image is saved to `output/mapa{YEAR}.png`.
