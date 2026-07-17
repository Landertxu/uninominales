"""Party data parser.

Reads party configuration from YAML files:
  - data/partidos/parties.yaml: Central party metadata (names, colors)
  - data/partidos/{year}/{region}.yaml: Per-election party codes and transfers
"""

import os
import yaml


_PARTIES_CACHE = None


def load_parties_metadata(path="data/partidos/parties.yaml"):
    """Load central party metadata (names and colors).

    Returns dict mapping party_name -> {"name": str, "color": str}.
    """
    global _PARTIES_CACHE
    if _PARTIES_CACHE is not None:
        return _PARTIES_CACHE

    with open(path) as f:
        _PARTIES_CACHE = yaml.safe_load(f)
    return _PARTIES_CACHE


def get_party_color(party_name, path="data/partidos/parties.yaml"):
    """Get the hex color for a party."""
    meta = load_parties_metadata(path)
    if party_name in meta:
        return meta[party_name].get("color", "#B4B4B4")
    return "#B4B4B4"


def get_all_party_colors(path="data/partidos/parties.yaml"):
    """Get all party colors as a dict mapping party_name -> hex_color."""
    meta = load_parties_metadata(path)
    return {name: info.get("color", "#B4B4B4") for name, info in meta.items()}


def read_party_file(path):
    """Read a per-election party file.

    Returns (codes, transfers) where:
    - codes: dict mapping numeric candidatura code (int) -> party name (str)
    - transfers: dict mapping party name -> {target_party: fraction, ...}
    """
    with open(path) as f:
        data = yaml.safe_load(f)

    codes = {}
    for party, code_list in data.get("parties", {}).items():
        for code in code_list:
            codes[int(code)] = party

    transfers = {}
    for party_from, targets in data.get("transfers", {}).items():
        transfers[party_from] = dict(targets) if targets else {}

    return codes, transfers
