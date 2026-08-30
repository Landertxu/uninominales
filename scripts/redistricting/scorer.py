"""Fitness function scorer for constituency divisions."""

from collections import defaultdict

from scripts.redistricting.loader import (
    assign_sections,
    section_to_district,
    section_to_municipality,
)
from scripts.redistricting.geometry import connected_components, union_area_and_perimeter


def score_constituency(name, sections, population, section_geoms=None, adjacency=None):
    """Compute score components for a single constituency."""
    pop = sum(population[s] for s in sections if s in population)
    municipalities = {section_to_municipality(s) for s in sections}
    districts = {section_to_district(s) for s in sections}

    stats = {
        "population": pop,
        "num_sections": len(sections),
        "municipalities": municipalities,
        "districts": districts,
    }

    if section_geoms is not None and adjacency is not None:
        # Contiguity: 3 points per extra connected component
        components = connected_components(sections, adjacency)
        stats["connected_components"] = components
        stats["contiguity_penalty"] = 3 * max(0, components - 1)

        # Compactness: penalty based on deviation from a perfect circle.
        # Using Polsby-Popper deviation: P^2 / (4*pi*A) - 1, which is 0 for a circle.
        import math

        area, perimeter = union_area_and_perimeter(section_geoms, sections)
        stats["area"] = area
        stats["perimeter"] = perimeter
        if area > 0:
            stats["compactness_penalty"] = (perimeter ** 2) / (4 * math.pi * area) - 1
        else:
            stats["compactness_penalty"] = 0.0
    else:
        stats["connected_components"] = None
        stats["contiguity_penalty"] = 0.0
        stats["area"] = 0.0
        stats["perimeter"] = 0.0
        stats["compactness_penalty"] = 0.0

    return stats


def score_province(province_code, constituencies, population, section_geoms=None, adjacency=None):
    """Compute fitness scores for one province."""
    assignment = assign_sections(constituencies, population)

    # Group sections by constituency
    sections_by_constituency = defaultdict(list)
    for section, constituency in assignment.items():
        sections_by_constituency[constituency].append(section)

    # Compute per-constituency stats
    constituency_stats = {}
    for name, sections in sections_by_constituency.items():
        constituency_stats[name] = score_constituency(
            name, sections, population, section_geoms, adjacency
        )

    # Province totals
    total_pop = sum(stats["population"] for stats in constituency_stats.values())
    num_seats = len(constituency_stats)
    ideal_pop = total_pop / num_seats if num_seats > 0 else 0

    # Population equality penalty: 1 point per 1% deviation from ideal
    pop_penalty = 0.0
    for stats in constituency_stats.values():
        if ideal_pop > 0:
            deviation = abs(stats["population"] - ideal_pop) / ideal_pop
            pop_penalty += deviation * 100  # 1 point per 1%

    # Municipality splitting penalty: 1 point per municipality split across constituencies
    municipality_constituencies = defaultdict(set)
    for name, stats in constituency_stats.items():
        for mun in stats["municipalities"]:
            municipality_constituencies[mun].add(name)
    municipality_split_penalty = sum(
        len(constituencies) - 1
        for constituencies in municipality_constituencies.values()
        if len(constituencies) > 1
    )

    # Census district splitting penalty: 2 points per district split across constituencies
    district_constituencies = defaultdict(set)
    for name, stats in constituency_stats.items():
        for district in stats["districts"]:
            district_constituencies[district].add(name)
    district_split_penalty = 2 * sum(
        len(constituencies) - 1
        for constituencies in district_constituencies.values()
        if len(constituencies) > 1
    )

    # Geometry-based penalties
    contiguity_penalty = sum(stats["contiguity_penalty"] for stats in constituency_stats.values())
    compactness_penalty = sum(stats["compactness_penalty"] for stats in constituency_stats.values())

    total_penalty = (
        pop_penalty
        + municipality_split_penalty
        + district_split_penalty
        + contiguity_penalty
        + compactness_penalty
    )

    return {
        "province": province_code,
        "seats": num_seats,
        "total_population": total_pop,
        "ideal_population": ideal_pop,
        "population_penalty": pop_penalty,
        "municipality_split_penalty": municipality_split_penalty,
        "district_split_penalty": district_split_penalty,
        "contiguity_penalty": contiguity_penalty,
        "compactness_penalty": compactness_penalty,
        "total_penalty": total_penalty,
        "constituencies": constituency_stats,
    }


