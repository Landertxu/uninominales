# Simulador de Elecciones Generales - Sistema Uninominal Mayoría Simple (UMS)

Simula elecciones generales españolas bajo el sistema de distritos uninominales (first-past-the-post) usando datos oficiales del INE.

## Quick Start

```bash
# 1. Create a virtual environment (once)
python3 -m venv env
source env/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run complete workflow (parse data + simulate + generate map)
python3 run.py

# Or specify a year
python3 run.py --year 2015
```

## Workflow Options

```bash
# Skip map rendering (generate shapefile only)
python3 run.py --skip-map

# Don't generate shapefile (print results only)
python3 run.py --no-map

# Just render the map from an existing shapefile (fast)
python3 run.py --viz-only

# Simulation method: 'transfer' (two-round with vote transfer) or
# 'plurality' (simple FPTP, no transfers). Default: transfer
python3 run.py --method plurality

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
│   ├── party_parser.py       # Party transfer file parser (YAML)
│   ├── constituency_parser.py # Constituency definition parser
│   ├── simulation.py         # FPTP vote transfer simulation
│   ├── election_runner.py    # Simulation orchestrator
│   ├── shapefile_gen.py      # Shapefile generator
│   └── visualization/        # Map renderer (package)
│       ├── __init__.py       # render_map() entry point
│       ├── core.py           # Core drawing utilities
│       ├── config.py         # Party colors and constants
│       ├── canarias.py       # Canary Islands relocation
│       ├── insets.py         # Madrid / Barcelona inset maps
│       └── connections.py    # Island connection boxes
├── data/                     # Input data
│   ├── raw/                  # INE election DAT files (2008, 2011, 2015)
│   ├── circunscripciones/    # 52 flat province files (circ01..circ52.dat)
│   ├── partidos/             # Party transfer files (YAML)
│   │   ├── parties.yaml      # Central party names and colors
│   │   ├── 2008/             # Per-region files for 2008
│   │   ├── 2011/             # Per-region files for 2011
│   │   ── 2015/             # Per-region files for 2015
│   ├── regions.dat           # Province-code -> region-name mapping
│   └── mapas/molde/          # Template census-section shapefile
├── output/                   # Generated outputs
├── requirements.txt          # Python dependencies
└── README.md
```

## How It Works

1. **Data Parsing** (`src/dat_parser.py`)
   - Parses INE fixed-width DAT files (candidatura data per census section)
   - Aggregates votes by census section and party

2. **Simulation** (`src/simulation.py` + `src/election_runner.py`)
   - For each constituency defined in `circXX.dat`:
     - Queries the preloaded data for all party votes within that district
     - Applies transfer rules: eliminated parties' votes flow to other parties
     - The party with the most votes after transfers wins the seat
   - The special party `R` (resto) collects votes of minor/unknown candidaturas
     and is always redistributed — it cannot win a seat
   - Returns winners and constituency mappings

3. **Shapefile Generation** (`src/shapefile_gen.py`)
   - Reads the template census-section shapefile
   - Adds CIRC (constituency) and PARTIDO (winning party) columns
   - Saves to `output/mapa{YEAR}.shp`

4. **Visualization** (`src/visualization/`)
   - Renders the shapefile to a PNG image
   - Detects constituency borders using unique-color technique
   - Relocates Canary Islands to bottom-left corner
   - Draws Madrid and Barcelona inset maps with connector lines
   - Draws party-colored constituencies with legend

## Data Files

- **data/raw/** — INE election DAT files (2008, 2011, 2015)
- **data/circunscripciones/** — 52 flat province files (one per province, circ01..circ52)
- **data/partidos/** — Per-year, per-region YAML files with party codes and vote transfers
- **data/partidos/parties.yaml** — Central party names and visualization colors
- **data/regions.dat** — Maps each province code to the region whose party file applies
- **data/mapas/molde/** — Template census-section shapefile

## INE DAT File Format (36 chars/line)

| Field | Position | Description |
|-------|----------|-------------|
| Process type | 0:2 | Process code (e.g. '02' for general elections) |
| Year | 2:6 | Election year (e.g. '2015') |
| Month | 6:8 | Election month |
| Round | 8:11 | Round/region constant (e.g. '100') |
| CUSEC | 11:21 | Census section: province(2) + municipality(3) + district(2) + section(3) |
| Space | 21 | Separator |
| Category | 22 | Candidatura letter code (data category, NOT party ID) |
| Candidatura | 23:29 | 6-digit numeric code (maps to party via party files) |
| Votes | 29:36 | Vote count (7 digits, zero-padded) |

## Output

Results are saved to `output/mapa{YEAR}.shp` with fields:
- All original census-section shapefile fields
- `CIRC` — Constituency name
- `PARTIDO` — Winning party abbreviation

The map image is saved to `output/mapa{YEAR}.png`.
