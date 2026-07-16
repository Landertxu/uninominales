"""INE DAT file parser.

Parses type-10 DAT files (candidatura data per census section) from the
Instituto Nacional de Estadistica (INE).

DAT file format (fixed-width, 36 chars per line):
  [0:5]   Process prefix (type + year + month)
  [5:8]   Round/region constant (e.g., '100' for 2015 general election)
  [8:11]  Province code (2 digits, zero-padded to 3)
  [11:21] Census section code (CUSEC): municipality(3) + district(2) + section(3)
          Full CUSEC = province(2) + municipality(3) + district(2) + section(3) = 10 chars
  [21]    Space
  [22]    Candidatura letter code (data category, not used for party ID)
  [23:29] Numeric candidatura code (6 digits, maps to party via party files)
  [29:36] Votes received (7 digits, zero-padded)
"""

from collections import defaultdict

RECORD_LEN = 36


def parse_dat_file(filepath):
    """Parse a type-10 INE DAT file.

    Yields (cusec, candidatura, votos) tuples where:
    - cusec: 10-char census section code (province+municipality+district+section)
    - candidatura: 6-char numeric party code
    - votos: integer vote count
    """
    agg = defaultdict(int)

    with open(filepath, "r", encoding="ascii", errors="replace") as f:
        for line in f:
            line = line.rstrip("\r\n")
            if len(line) < RECORD_LEN:
                continue

            cusec = line[11:21]
            candidatura = line[23:29]
            votes_str = line[29:36]

            try:
                votos = int(votes_str)
            except ValueError:
                continue

            agg[(cusec, candidatura)] += votos

    for (cusec, candidatura), votos in agg.items():
        yield (cusec, candidatura, votos)
