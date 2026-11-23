import math

import pytest

from parity.metrics import audit, is_fragile, to_outcomes, two_proportion_p


def rows(spec):
    """spec: {group: (n, positives)} -> list of row dicts."""
    out = []
    for group, (n, pos) in spec.items():
        out += [{"g": group, "y": "1" if i < pos else "0"} for i in range(n)]
    return out


def groups(result, dim=0):
    return {g.name: g for g in result.dimensions[dim].groups}


def test_impact_ratio_and_reference():
    r = audit(rows({"A": (100, 50), "B": (100, 30)}), "y", ["g"])
    g = groups(r)
    assert g["A"].status == "reference" and g["A"].impact_ratio == 1.0
    assert g["B"].impact_ratio == pytest.approx(0.6)
    assert g["B"].status == "adverse"
    assert r.has_adverse_impact


def test_exactly_four_fifths_passes():
    g = groups(audit(rows({"A": (100, 50), "B": (100, 40)}), "y", ["g"]))
    assert g["B"].impact_ratio == pytest.approx(0.8)
    assert g["B"].status == "ok"


def test_small_groups_reported_but_not_flagged_or_used_as_reference():
    # C is 1% of the sample with a perfect rate: it must not become the reference.
    r = audit(rows({"A": (500, 250), "B": (490, 100), "C": (10, 10)}), "y", ["g"])
    g = groups(r)
    assert g["A"].status == "reference"
    assert g["C"].status == "excluded"
    assert g["B"].status == "adverse"


def test_unknowns_counted_not_guessed():
    data = rows({"A": (50, 25), "B": (50, 25)}) + [{"g": "", "y": "1"}, {"g": "Prefer not to say", "y": "0"}]
    d = audit(data, "y", ["g"]).dimensions[0]
    assert d.unknown == 2
    assert sum(g.n for g in d.groups) == 100


def test_intersectional_dimension():
    data = [{"sex": s, "race": r, "y": "1"} for s in ("F", "M") for r in ("X", "Y")] * 10
    r = audit(data, "y", ["sex", "race"])
    assert [d.name for d in r.dimensions] == ["sex", "race", "sex × race"]
    assert {g.name for g in r.dimensions[2].groups} == {"F · X", "F · Y", "M · X", "M · Y"}
    assert len(audit(data, "y", ["sex", "race"], intersect=False).dimensions) == 2


def test_scoring_mode_uses_median():
    assert to_outcomes(["1", "2", "3", "4", "5"], scored=True) == [False, False, False, True, True]
    with pytest.raises(ValueError):
        to_outcomes(["1", "oops"], scored=True)


def test_selection_values_are_forgiving():
    assert to_outcomes(["Yes", " hired ", "1", True, 1, "no", "0", None]) == [True] * 5 + [False] * 3


def test_p_value_matches_known_z_test():
    # 50/100 vs 30/100 -> z ≈ 2.887, p ≈ 0.0039
    assert two_proportion_p(50, 100, 30, 100) == pytest.approx(0.00389, abs=1e-4)
    assert two_proportion_p(0, 10, 0, 10) == 1.0


def test_fragility():
    # ref rate 0.5, threshold 0.8 -> pass line is 0.4
    assert is_fragile(3, 10, 0.5, 0.8)        # 0.3 fails; 0.4 would pass
    assert not is_fragile(10, 100, 0.5, 0.8)  # 0.10 fails; 0.11 still fails
    assert is_fragile(4, 10, 0.5, 0.8)        # 0.4 passes; 0.3 would fail


def test_all_zero_rates_do_not_crash():
    g = groups(audit(rows({"A": (10, 0), "B": (10, 0)}), "y", ["g"]))
    assert all(x.impact_ratio is None for x in g.values())
    assert not any(x.status == "adverse" for x in g.values())


def test_missing_column_is_a_clear_error():
    with pytest.raises(ValueError, match="missing column"):
        audit([{"g": "A", "y": "1"}], "y", ["race"])
