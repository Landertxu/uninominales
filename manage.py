#!/usr/bin/env python3
"""
Management script for constituency validation and population analysis.
"""

import argparse
import csv
import os
import sys
from collections import defaultdict
from pathlib import Path

from src.constituency_parser import parse_constituency_file


def load_population_data(csv_path):
    """
    Load population data from CSV file.
    
    Returns:
        dict: Mapping of seccion_censal (str) -> population (int)
    """
    population_data = {}
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            seccion = row['seccion_censal']
            population = int(row['population'])
            population_data[seccion] = population
    
    return population_data


def load_all_constituencies(census_dir):
    """
    Load all constituency definitions from circXX.dat files.
    
    Returns:
        list: List of (constituency_name, inclusion_codes, exclusion_codes, province_code) tuples
    """
    constituencies = []
    constituencies_path = Path(census_dir) / 'constituencies'
    
    if not constituencies_path.exists():
        raise FileNotFoundError(f"Constituencies directory not found: {constituencies_path}")
    
    # Find all circXX.dat files
    circ_files = sorted(constituencies_path.glob('circ*.dat'))
    
    for circ_file in circ_files:
        # Extract province code from filename (e.g., circ01.dat -> 01)
        province_code = circ_file.stem[4:]  # Remove 'circ' prefix
        file_constituencies = parse_constituency_file(circ_file)
        for constituency_name, inclusion_codes, exclusion_codes in file_constituencies:
            constituencies.append((constituency_name, inclusion_codes, exclusion_codes, province_code))
    
    return constituencies


def assign_sections_to_constituencies(population_data, constituencies):
    """
    Assign each section to its constituency using prefix matching.
    
    Returns:
        dict: Mapping of constituency_name -> {
            'sections': list of section codes,
            'population': total population,
            'province_code': province code
        }
    """
    constituency_assignments = {}
    
    for constituency_name, inclusion_codes, exclusion_codes, province_code in constituencies:
        constituency_assignments[constituency_name] = {
            'sections': [],
            'population': 0,
            'province_code': province_code
        }
    
    # For each section in population data, find its constituency
    for section in population_data.keys():
        matched_constituency = None
        
        for constituency_name, inclusion_codes, exclusion_codes, province_code in constituencies:
            # Check if section matches any inclusion code
            matches_inclusion = any(section.startswith(inc) for inc in inclusion_codes)
            
            # Check if section matches any exclusion code
            matches_exclusion = any(section.startswith(exc) for exc in exclusion_codes)
            
            # Section belongs to this constituency if it matches inclusion and not exclusion
            if matches_inclusion and not matches_exclusion:
                if matched_constituency is not None:
                    # Duplicate coverage - will be handled in validation
                    pass
                else:
                    matched_constituency = constituency_name
        
        if matched_constituency is not None:
            constituency_assignments[matched_constituency]['sections'].append(section)
            constituency_assignments[matched_constituency]['population'] += population_data[section]
    
    return constituency_assignments


def validate_coverage(population_data, constituencies, constituency_assignments):
    """
    Check for missing, duplicate, or uncovered sections.
    
    Returns:
        dict: {
            'missing': list of sections not covered by any constituency,
            'duplicate': dict of section -> list of constituencies covering it,
            'uncovered': list of sections in population data with no constituency match
        }
    """
    validation = {
        'missing': [],
        'duplicate': {},
        'uncovered': []
    }
    
    # Track which sections are covered and by which constituencies
    section_coverage = defaultdict(list)
    
    for section in population_data.keys():
        for constituency_name, inclusion_codes, exclusion_codes, province_code in constituencies:
            # Check if section matches any inclusion code
            matches_inclusion = any(section.startswith(inc) for inc in inclusion_codes)
            
            # Check if section matches any exclusion code
            matches_exclusion = any(section.startswith(exc) for exc in exclusion_codes)
            
            # Section belongs to this constituency if it matches inclusion and not exclusion
            if matches_inclusion and not matches_exclusion:
                section_coverage[section].append(constituency_name)
    
    # Identify issues
    for section in population_data.keys():
        coverage = section_coverage[section]
        
        if len(coverage) == 0:
            # Section not covered by any constituency
            validation['uncovered'].append(section)
        elif len(coverage) > 1:
            # Section covered by multiple constituencies
            validation['duplicate'][section] = coverage
    
    return validation


def check_constituencies(args):
    """
    Validate constituency definitions against population data.
    """
    census_dir = args.census_dir
    population_file = args.population_file
    
    # Determine population file path
    if population_file is None:
        # Try to find population file in census directory
        census_path = Path(census_dir)
        census_name = census_path.name  # e.g., 'spain2011'
        year = census_name.replace('spain', '')  # e.g., '2011'
        population_file = census_path / 'population' / f'{year}.csv'
    
    # Check if files exist
    if not os.path.exists(population_file):
        print(f"Error: Population file not found: {population_file}")
        sys.exit(1)
    
    constituencies_path = Path(census_dir) / 'constituencies'
    if not constituencies_path.exists():
        print(f"Error: Constituencies directory not found: {constituencies_path}")
        sys.exit(1)
    
    # Load data
    print(f"Loading population data from: {population_file}")
    population_data = load_population_data(population_file)
    print(f"Total sections in population data: {len(population_data):,}")
    
    print(f"\nLoading constituency definitions from: {constituencies_path}")
    constituencies = load_all_constituencies(census_dir)
    print(f"Total constituencies: {len(constituencies)}")
    
    # Assign sections to constituencies
    print("\nAssigning sections to constituencies...")
    constituency_assignments = assign_sections_to_constituencies(population_data, constituencies)
    
    # Validate coverage
    print("Validating coverage...")
    validation = validate_coverage(population_data, constituencies, constituency_assignments)
    
    # Print report
    print("\n" + "=" * 60)
    print("=== Constituency Validation Report ===")
    print("=" * 60)
    print(f"Census: {census_dir}")
    print(f"Population file: {population_file}")
    print(f"Total sections in population data: {len(population_data):,}")
    
    covered_sections = sum(len(assignment['sections']) for assignment in constituency_assignments.values())
    print(f"Sections covered by constituencies: {covered_sections:,}")
    
    # Print warnings
    has_warnings = False
    
    if validation['uncovered']:
        has_warnings = True
        print(f"\nWARNINGS:")
        print(f"- {len(validation['uncovered'])} sections not covered by any constituency")
        if len(validation['uncovered']) <= 10:
            print(f"  Examples: {', '.join(validation['uncovered'][:10])}")
        else:
            print(f"  Examples: {', '.join(validation['uncovered'][:5])}, ...")
    
    if validation['duplicate']:
        has_warnings = True
        print(f"\n- {len(validation['duplicate'])} sections covered by multiple constituencies")
        if len(validation['duplicate']) <= 10:
            for section, constituencies_list in list(validation['duplicate'].items())[:10]:
                print(f"  {section}: {', '.join(constituencies_list)}")
        else:
            for section, constituencies_list in list(validation['duplicate'].items())[:5]:
                print(f"  {section}: {', '.join(constituencies_list)}")
            print(f"  ...")
    
    if not has_warnings:
        print("\n✓ All sections are properly covered!")
    
    # Print population by constituency
    print("\n" + "=" * 60)
    print("=== Population by Constituency ===")
    print("=" * 60)
    
    total_population = 0
    for constituency_name in sorted(constituency_assignments.keys()):
        assignment = constituency_assignments[constituency_name]
        population = assignment['population']
        total_population += population
        print(f"{constituency_name}: {population:,}")
    
    print(f"\nTotal population: {total_population:,}")
    
    # Exit with error code if there are issues
    if has_warnings:
        sys.exit(1)


def population_stats(args):
    """
    Show population statistics for constituencies.
    """
    census_dir = args.census_dir
    population_file = args.population_file
    
    # Determine population file path
    if population_file is None:
        # Try to find population file in census directory
        census_path = Path(census_dir)
        census_name = census_path.name  # e.g., 'spain2011'
        year = census_name.replace('spain', '')  # e.g., '2011'
        population_file = census_path / 'population' / f'{year}.csv'
    
    # Check if files exist
    if not os.path.exists(population_file):
        print(f"Error: Population file not found: {population_file}")
        sys.exit(1)
    
    constituencies_path = Path(census_dir) / 'constituencies'
    if not constituencies_path.exists():
        print(f"Error: Constituencies directory not found: {constituencies_path}")
        sys.exit(1)
    
    # Load data
    print(f"Loading population data from: {population_file}")
    population_data = load_population_data(population_file)
    
    print(f"Loading constituency definitions from: {constituencies_path}")
    constituencies = load_all_constituencies(census_dir)
    
    # Assign sections to constituencies
    constituency_assignments = assign_sections_to_constituencies(population_data, constituencies)
    
    # Calculate statistics
    populations = [assignment['population'] for assignment in constituency_assignments.values()]
    
    if not populations:
        print("Error: No population data found for constituencies")
        sys.exit(1)
    
    total_population = sum(populations)
    num_constituencies = len(populations)
    avg_population = total_population / num_constituencies
    
    # Find min and max
    min_pop = min(populations)
    max_pop = max(populations)
    
    # Find which constituencies have min and max
    min_constituency = [name for name, assignment in constituency_assignments.items() 
                        if assignment['population'] == min_pop]
    max_constituency = [name for name, assignment in constituency_assignments.items() 
                        if assignment['population'] == max_pop]
    
    # Calculate standard deviation
    variance = sum((p - avg_population) ** 2 for p in populations) / num_constituencies
    std_dev = variance ** 0.5
    
    # Print statistics
    print("\n" + "=" * 60)
    print("=== Population Statistics ===")
    print("=" * 60)
    print(f"Total constituencies: {num_constituencies}")
    print(f"Total population: {total_population:,}")
    print(f"Average population per constituency: {avg_population:,.0f}")
    print(f"Min: {min_pop:,} ({', '.join(min_constituency)})")
    print(f"Max: {max_pop:,} ({', '.join(max_constituency)})")
    print(f"Std dev: {std_dev:,.0f}")


def population_by_province(args):
    """
    Show population by constituency grouped by province.
    """
    census_dir = args.census_dir
    population_file = args.population_file
    
    # Determine population file path
    if population_file is None:
        # Try to find population file in census directory
        census_path = Path(census_dir)
        census_name = census_path.name  # e.g., 'spain2011'
        year = census_name.replace('spain', '')  # e.g., '2011'
        population_file = census_path / 'population' / f'{year}.csv'
    
    # Check if files exist
    if not os.path.exists(population_file):
        print(f"Error: Population file not found: {population_file}")
        sys.exit(1)
    
    constituencies_path = Path(census_dir) / 'constituencies'
    if not constituencies_path.exists():
        print(f"Error: Constituencies directory not found: {constituencies_path}")
        sys.exit(1)
    
    # Load data
    print(f"Loading population data from: {population_file}")
    population_data = load_population_data(population_file)
    
    print(f"Loading constituency definitions from: {constituencies_path}")
    constituencies = load_all_constituencies(census_dir)
    
    # Assign sections to constituencies
    constituency_assignments = assign_sections_to_constituencies(population_data, constituencies)
    
    # Group by province
    province_groups = defaultdict(list)
    for constituency_name, assignment in constituency_assignments.items():
        province_code = assignment['province_code']
        province_groups[province_code].append((constituency_name, assignment['population']))
    
    # Print results
    print("\n" + "=" * 60)
    print("=== Population by Province ===")
    print("=" * 60)
    
    grand_total = 0
    for province_code in sorted(province_groups.keys()):
        constituencies_list = province_groups[province_code]
        province_total = sum(pop for _, pop in constituencies_list)
        grand_total += province_total
        
        print(f"\nProvince {province_code}:")
        print("-" * 40)
        for constituency_name, population in sorted(constituencies_list, key=lambda x: x[1], reverse=True):
            print(f"  {constituency_name}: {population:,}")
        print(f"  {'Total:':<30} {province_total:,}")
    
    print("\n" + "=" * 60)
    print(f"Grand Total: {grand_total:,}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Management script for constituency validation and population analysis"
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # check-constituencies command
    check_parser = subparsers.add_parser(
        'check-constituencies',
        help='Validate constituency definitions against population data'
    )
    check_parser.add_argument(
        '--census-dir',
        required=True,
        help='Path to census directory (e.g., data/census/spain2011)'
    )
    check_parser.add_argument(
        '--population-file',
        help='Optional override for population CSV path'
    )
    
    # population-stats command
    stats_parser = subparsers.add_parser(
        'population-stats',
        help='Show population statistics for constituencies'
    )
    stats_parser.add_argument(
        '--census-dir',
        required=True,
        help='Path to census directory (e.g., data/census/spain2011)'
    )
    stats_parser.add_argument(
        '--population-file',
        help='Optional override for population CSV path'
    )
    
    # population-by-province command
    province_parser = subparsers.add_parser(
        'population-by-province',
        help='Show population by constituency grouped by province'
    )
    province_parser.add_argument(
        '--census-dir',
        required=True,
        help='Path to census directory (e.g., data/census/spain2011)'
    )
    province_parser.add_argument(
        '--population-file',
        help='Optional override for population CSV path'
    )
    
    args = parser.parse_args()
    
    if args.command == 'check-constituencies':
        check_constituencies(args)
    elif args.command == 'population-stats':
        population_stats(args)
    elif args.command == 'population-by-province':
        population_by_province(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
