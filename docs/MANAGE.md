# Manage.py - Constituency Management Tool

A management script for validating constituency definitions against census population data and computing population statistics.

## Overview

The `manage.py` script provides tools to:
- Validate that every census section belongs to exactly one constituency
- Detect missing or duplicate coverage
- Calculate population statistics per constituency
- Analyze population distribution across constituencies

## Data Format

### Population Data

Population data is stored in CSV format with the following structure:

```csv
seccion_censal,population
0100101001,1383
0100101002,1542
```

- `seccion_censal`: 10-digit INE census section code
- `population`: Integer population count

### Directory Structure

```
data/census/
├── spain2011/
│   ├── constituencies/
│   │   ├── circ01.dat
│   │   ├── circ02.dat
│   │   └── ...
│   └── population/
│       └── 2011.csv
```

## Usage

### 1. Check Constituencies

Validates that every census section in the population data is covered by exactly one constituency.

```bash
python manage.py check-constituencies --census-dir data/census/spain2011
```

**Options:**
- `--census-dir`: Path to census directory (required)
- `--population-file`: Optional override for population CSV path

**Output:**
- Total sections in population data
- Sections covered by constituencies
- Warnings for uncovered or duplicate sections
- Population breakdown by constituency

**Example output:**
```
============================================================
=== Constituency Validation Report ===
============================================================
Census: data/census/spain2011
Population file: data/census/spain2011/population/2011.csv
Total sections in population data: 36,127
Sections covered by constituencies: 36,127

✓ All sections are properly covered!

============================================================
=== Population by Constituency ===
============================================================
alava1: 154,863
alava2: 167,069
...
Total population: 46,771,341
```

### 2. Population Statistics

Shows statistical summary of population distribution across constituencies.

```bash
python manage.py population-stats --census-dir data/census/spain2011
```

**Options:**
- `--census-dir`: Path to census directory (required)
- `--population-file`: Optional override for population CSV path

**Output:**
- Total number of constituencies
- Total population
- Average population per constituency
- Minimum and maximum population (with constituency names)
- Standard deviation

**Example output:**
```
============================================================
=== Population Statistics ===
============================================================
Total constituencies: 350
Total population: 46,771,341
Average population per constituency: 133,632
Min: 84,509 (meilla1)
Max: 185,432 (zamora1)
Std dev: 12,960
```

### 3. Population by Province

Shows population by constituency grouped by province.

```bash
python manage.py population-by-province --census-dir data/census/spain2011
```

**Options:**
- `--census-dir`: Path to census directory (required)
- `--population-file`: Optional override for population CSV path

**Output:**
- Constituencies grouped by province code
- Population for each constituency
- Total population per province
- Grand total population

**Example output:**
```
============================================================
=== Population by Province ===
============================================================

Province 01:
----------------------------------------
  alava1: 154,863
  alava2: 167,069
  Total:                         321,932

Province 02:
----------------------------------------
  albacete1: 130,414
  albacete2: 137,564
  albacete3: 129,009
  Total:                         396,987

...

============================================================
Grand Total: 46,771,341
============================================================
```

## How It Works

### Section Matching

A census section is assigned to a constituency based on prefix matching:

1. **Inclusion**: The section code must start with at least one inclusion prefix defined in the constituency
2. **Exclusion**: The section code must NOT start with any exclusion prefix defined in the constituency

### Validation Checks

The script performs three validation checks:

1. **Missing sections**: Sections in population data not covered by any constituency
2. **Duplicate coverage**: Sections covered by multiple constituencies
3. **Uncovered sections**: Sections in population data with no constituency match

### Error Handling

- File not found: Clear error message with expected path
- Invalid CSV format: Line number and error description
- Invalid constituency file: Line number and error description

## Data Sources

### 2011 Census Data

The 2011 population data was converted from INE (Instituto Nacional de Estadística) census data:
- Source: `old/uninominales/auxiliar/0001.csv`
- Converted to standard format: `data/census/spain2011/population/2011.csv`
- Total sections: 36,127
- Total population: 46,771,341

### Future Census Data

The script is designed to support multiple census years. To add a new census year:

1. Create directory: `data/census/spainYYYY/`
2. Add population data: `data/census/spainYYYY/population/YYYY.csv`
3. Add constituency definitions: `data/census/spainYYYY/constituencies/circ*.dat`

## Examples

### Check 2011 constituencies

```bash
python manage.py check-constituencies --census-dir data/census/spain2011
```

### Get population statistics

```bash
python manage.py population-stats --census-dir data/census/spain2011
```

### View population by province

```bash
python manage.py population-by-province --census-dir data/census/spain2011
```

### Use custom population file

```bash
python manage.py check-constituencies \
  --census-dir data/census/spain2011 \
  --population-file /path/to/custom/population.csv
```

## Exit Codes

- `0`: Success (all validations passed)
- `1`: Validation errors found (missing or duplicate sections)
- `1`: File not found or invalid format

## Future Enhancements

- Support for multiple census years in a single run
- Comparison of population changes between census years
- Visualization of constituency population distribution
- Automatic suggestion of boundary adjustments based on population imbalance
