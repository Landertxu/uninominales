"""Constituency definition file parser.

Reads constituency definition files (circXX.dat) that map INE census section
codes to single-member districts.

File format:
  - Lines starting with '#' are comments
  - Empty lines are ignored
  - Constituency name lines end with ':' (e.g., 'circ1001:')
  - Inclusion lines: INE code prefix that matches sections in this constituency
  - Exclusion lines: Lines starting with '-' define sections to exclude
"""


def parse_constituency_file(path):
    """Parse a constituency definition file.

    Returns a list of (constituency_name, inclusion_codes, exclusion_codes) tuples.
    """
    constituencies = []
    current_name = None
    inclusions = []
    exclusions = []

    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.endswith(":"):
                if current_name is not None:
                    constituencies.append((current_name, inclusions, exclusions))
                current_name = line[:-1]
                inclusions = []
                exclusions = []
            elif line.startswith("-"):
                exclusions.append(line[1:])
            else:
                inclusions.append(line)

    if current_name is not None:
        constituencies.append((current_name, inclusions, exclusions))

    return constituencies
