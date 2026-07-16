"""Party transfer file parser.

Reads party transfer files that map numeric candidatura codes to party names
and define vote transfer rules for the FPTP simulation.

File format:
  - Lines starting with '#' are comments
  - Party definition lines: 'PARTY_NAME: CODE1 CODE2 ...'
  - Transfer lines: 'SOURCE_PARTY TARGET1 FRACTION1 TARGET2 FRACTION2 ...'
"""


def read_party_file(path):
    """Read a party transfer file.

    Returns (codes, transfers) where:
    - codes: dict mapping numeric candidatura code (int) -> party name (str)
    - transfers: dict mapping party name -> {target_party: fraction, ...}
    """
    codes = {}
    transfers = {}

    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            parts = line.split()
            if parts[0].endswith(":"):
                party = parts[0][:-1]
                for code_str in parts[1:]:
                    codes[int(code_str)] = party
            else:
                party_from = parts[0]
                transfers[party_from] = {}
                i = 1
                while i + 1 < len(parts):
                    target = parts[i]
                    fraction = float(parts[i + 1])
                    transfers[party_from][target] = fraction
                    i += 2

    return codes, transfers
