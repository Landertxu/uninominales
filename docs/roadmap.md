# Roadmap: Automated Constituency Division

## Goal

Build a tool that, given census population data and census-section geometry, automatically proposes constituency divisions that satisfy legal hard constraints and optimize a configurable fitness function. The user can review and manually refine proposals before exporting them for election simulations.

## Hard constraints

- Total seats = 350.
- Each constituency elects exactly one representative.
- Seat allocation per province/island group follows configured legal rules (Phase 3).
- All census sections must be assigned to exactly one constituency.

## Fitness function (weighted, configurable)

- **Population equality:** penalty proportional to deviation from ideal population per seat.
- **Municipality integrity:** penalty for splitting municipalities.
- **Census-district integrity:** penalty for splitting census districts.
- **Contiguity:** penalty for non-connected components (soft, not required).
- **Compactness:** perimeter/area ratio penalty.

Default weights can be adjusted; the same weights apply to all provinces initially.

## Phase 0: Scorer for existing divisions (short term)

- Load population per census section from `data/census/{year}/population/`.
- Load an existing division (e.g. 2011 base from `data/geographic/spain2011/constituencies/`).
- Compute and print the fitness score per province and nationwide.
- Use this to tune weights and establish a baseline.
- Cleanup: remove stale `data/census/spain2021/constituencies/`.

## Phase 1: Single-province optimizer

- Pick a pilot province.
- Build adjacency graph from the shapefile.
- Implement simulated annealing with section moves/swaps.
- Hard constraints: correct number of constituencies, one seat each, every section assigned.
- Soft constraints: the fitness function above.
- Generate multiple candidate divisions from different starting points.
- Compare against the existing division.

## Phase 2: Full-country optimizer

- Run the optimizer independently for every province.
- Use hardcoded province seat allocations.
- Export a complete division as `.dat` files.
- Validate totals and contiguity.

## Phase 3: Configurable legal seat allocation

- Implement rules for distributing 350 seats:
  - Fixed seats for Ceuta, Melilla, island groups.
  - Largest remainder method for provinces.
  - Configurable minimum seats per province.
- Combine with the province optimizer for a fully automatic pipeline.

## Phase 4: Interactive review (long term)

- Visualize candidate divisions.
- Allow manual section moves with live score updates.
- Start with CLI/Jupyter; consider a web UI later.
