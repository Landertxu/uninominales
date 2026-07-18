"""Regression tests: exact seat counts by year."""

import pytest

from src.election_runner import run_simulation


# Seat totals from the current implementation. Update these intentionally if
# data or transfer rules change.
EXPECTED_SEATS = {
    "2008": {
        "PSOE": 198,
        "PP": 146,
        "PNV": 4,
        "CC": 1,
        "CiU": 1,
    },
    "2011": {
        "PP": 242,
        "PSOE": 69,
        "CiU": 25,
        "PNV": 8,
        "AMA": 6,
    },
    "2015": {
        "PP": 161,
        "P's": 85,
        "PSOE": 77,
        "C's": 11,
        "ERC": 10,
        "PNV": 5,
        "DL": 1,
    },
    "2016": {
        "PP": 223,
        "P's": 57,
        "PSOE": 52,
        "ERC": 10,
        "C's": 4,
        "PNV": 4,
    },
    "2019a": {
        "PSOE": 205,
        "PP": 62,
        "ERC": 39,
        "C's": 29,
        "PNV": 10,
        "EHB": 2,
        "CCa": 1,
        "JxCAT": 1,
        "ECP": 1,
    },
    "2019b": {
        "PSOE": 204,
        "PP": 87,
        "ERC": 41,
        "PNV": 9,
        "EHB": 4,
        "VOX": 2,
        "ECP": 2,
        "JxCAT": 1,
    },
}


@pytest.mark.parametrize("year", ["2008", "2011", "2015", "2016", "2019a", "2019b"])
def test_seat_totals_match_expected(year):
    """Run the full simulation and compare seat totals to the baseline."""
    from collections import Counter

    winners, _, _ = run_simulation(year)
    seats = Counter(winners.values())

    expected = EXPECTED_SEATS[year]

    # Same number of parties
    assert set(seats.keys()) == set(expected.keys()), (
        f"{year}: party mismatch. got {dict(seats)}, expected {expected}"
    )

    # Same seat count per party
    for party, expected_count in expected.items():
        assert seats[party] == expected_count, (
            f"{year} {party}: expected {expected_count}, got {seats[party]}"
        )

    # Total seats = 350
    assert sum(seats.values()) == 350


@pytest.mark.parametrize("year", ["2008", "2011", "2015", "2016", "2019a", "2019b"])
def test_no_r_wins_seat(year):
    """R is a catch-all and should never win a constituency."""
    winners, _, _ = run_simulation(year)
    assert "R" not in winners.values()


@pytest.mark.parametrize("year", ["2008", "2011", "2015", "2016", "2019a", "2019b"])
def test_all_constituencies_have_winner(year):
    """Every constituency should produce a winner."""
    winners, _, _ = run_simulation(year)
    assert all(winner is not None and winner != "" for winner in winners.values())
    assert len(winners) == 350
