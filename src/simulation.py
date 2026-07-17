"""FPTP election simulation logic.

Implements the vote transfer simulation for first-past-the-post elections.
"""

# Parties that are always eliminated and redistributed
RESTO_PARTY = "R"


def simulate_plurality(votes):
    """Determine the winner using simple plurality (no vote transfers).

    Args:
        votes: dict mapping party -> vote count

    Returns:
        The winning party name (not 'R').

    In simple plurality, the party with the most votes wins directly.
    'R' (resto/minor parties) is excluded from winning.
    """
    real_parties = {p: v for p, v in votes.items() if p != RESTO_PARTY}
    if not real_parties:
        return RESTO_PARTY
    return max(real_parties, key=real_parties.get)


def simulate_winner(votes, transfers):
    """Determine the winner using vote transfer simulation.

    Args:
        votes: dict mapping party -> vote count
        transfers: dict mapping party -> {target: fraction, ...}

    Returns:
        The winning party name (not 'R').

    In FPTP, 'R' (resto) is a catch-all for minor parties, not a competing
    party. It must always be eliminated and its votes redistributed.
    The 'second' set protects top parties from elimination — 'R' is excluded.
    """
    votes = dict(votes)

    real_parties = {p: v for p, v in votes.items() if p != RESTO_PARTY}
    if not real_parties:
        return RESTO_PARTY

    # Build the set of parties that cannot be eliminated
    second = set()
    best = max(v for p, v in votes.items() if p != RESTO_PARTY)
    total = sum(votes.values())

    for p, v in votes.items():
        if p == RESTO_PARTY:
            continue
        if v == best or v >= total / 5:
            second.add(p)

    # Iteratively redistribute votes from eliminated parties
    for _ in range(100):
        changed = False
        for p in list(votes.keys()):
            if p not in second and votes[p] > 0:
                old = votes[p]
                votes[p] = 0
                if p in transfers:
                    for np, ptr in transfers[p].items():
                        if np in votes:
                            votes[np] += old * ptr
                            changed = True
                elif RESTO_PARTY in votes:
                    votes[RESTO_PARTY] += old
                    changed = True
        if not changed:
            break

    # Winner is the real party (not 'R') with most votes after transfers
    return max(
        (p for p in votes if p != RESTO_PARTY),
        key=lambda p: votes.get(p, 0)
    )
