"""Unit tests for the FPTP simulation logic."""

from collections import Counter

import pytest

from src.simulation import simulate_plurality, simulate_winner, RESTO_PARTY


def test_simulate_plurality_simple_majority():
    votes = {"PP": 100, "PSOE": 60, "IU": 20}
    assert simulate_plurality(votes) == "PP"


def test_simulate_plurality_r_cannot_win():
    votes = {"PP": 100, "PSOE": 60, RESTO_PARTY: 500}
    assert simulate_plurality(votes) == "PP"


def test_simulate_plurality_only_r():
    votes = {RESTO_PARTY: 100}
    assert simulate_plurality(votes) == RESTO_PARTY


def test_simulate_winner_simple_majority():
    votes = {"PP": 100, "PSOE": 60, "IU": 20}
    transfers = {}
    assert simulate_winner(votes, transfers) == "PP"


def test_simulate_winner_r_redistributed():
    # R is eliminated and redistributed, should not win
    votes = {"PP": 100, "PSOE": 90, RESTO_PARTY: 50}
    transfers = {RESTO_PARTY: {"PP": 0.5, "PSOE": 0.3}}
    winner = simulate_winner(votes, transfers)
    # R redistributes: PP gets 25, PSOE gets 15 -> PP=125, PSOE=105
    assert winner == "PP"


def test_simulate_winner_small_party_eliminated():
    # IU below 20% threshold and not best, so it gets eliminated
    votes = {"PP": 100, "PSOE": 80, "IU": 15}
    transfers = {
        "IU": {"PSOE": 0.6, "PP": 0.2},
    }
    winner = simulate_winner(votes, transfers)
    # IU eliminated: PSOE gets 9, PP gets 3 -> PP=103, PSOE=89
    assert winner == "PP"


def test_simulate_winner_small_party_flip():
    # IU below threshold, but transfers push PSOE over PP
    votes = {"PP": 100, "PSOE": 95, "IU": 20}
    transfers = {
        "IU": {"PSOE": 0.6, "PP": 0.2},
    }
    winner = simulate_winner(votes, transfers)
    # IU eliminated: PSOE gets 12, PP gets 4 -> PP=104, PSOE=107
    assert winner == "PSOE"


def test_simulate_winner_best_party_protected():
    # Best party should not be eliminated even if it has <20%
    votes = {"PP": 100, "PSOE": 95, "IU": 20, "C's": 18}
    transfers = {
        "IU": {"PSOE": 1.0},
        "C's": {"PP": 1.0},
    }
    winner = simulate_winner(votes, transfers)
    # PP is best, C's is eliminated (not best, <20%)
    # C's -> PP: PP becomes 118, PSOE stays 95
    # IU is eliminated (not best, <20%): PSOE becomes 115
    # After first pass: PP=118, PSOE=115. PP wins.
    assert winner == "PP"


def test_simulate_winner_20pct_protected():
    # Party with >=20% is protected from elimination
    votes = {"PP": 100, "PSOE": 100, "IU": 100, RESTO_PARTY: 50}
    transfers = {
        RESTO_PARTY: {"PP": 1.0},
    }
    winner = simulate_winner(votes, transfers)
    # All three parties >= 20%, none eliminated. R redistributes to PP.
    assert winner == "PP"


def test_simulate_winner_tie_with_r():
    votes = {"PP": 100, "PSOE": 100, RESTO_PARTY: 50}
    transfers = {
        RESTO_PARTY: {"PP": 0.5, "PSOE": 0.5},
    }
    winner = simulate_winner(votes, transfers)
    # After R redistribution: PP=125, PSOE=125 -> tie
    # max() returns the first one encountered
    assert winner in {"PP", "PSOE"}


def test_simulate_winner_no_real_parties():
    votes = {RESTO_PARTY: 100}
    transfers = {RESTO_PARTY: {}}
    assert simulate_winner(votes, transfers) == RESTO_PARTY


def test_simulate_winner_transfer_to_missing_party():
    # Transfers to a party not in votes should not crash
    votes = {"PP": 100, "PSOE": 80, "IU": 15}
    transfers = {
        "IU": {"PSOE": 0.6, "VOX": 0.2},  # VOX not in votes
    }
    winner = simulate_winner(votes, transfers)
    # IU -> PSOE gets 9, VOX ignored -> PP=100, PSOE=89
    assert winner == "PP"


def test_simulate_winner_fractions_sum_less_than_one():
    # Unallocated fraction is lost
    votes = {"PP": 100, "PSOE": 90, "IU": 20}
    transfers = {
        "IU": {"PSOE": 0.4},  # 60% lost
    }
    winner = simulate_winner(votes, transfers)
    # IU -> PSOE gets 8 -> PP=100, PSOE=98
    assert winner == "PP"
