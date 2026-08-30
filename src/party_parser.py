"""Party data parser.

Reads per-election party configuration from YAML files:
  - data/partidos/{year}/{region}.yaml: party codes and transfers
"""

import yaml


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
