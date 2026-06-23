import pytest

from medicine_matcher import (
    build_composition_key,
    build_medicine_profile,
    compare_medicine_profiles,
    detect_formulation_variant,
)


def profile(name, composition, unit, discontinued=0):
    return build_medicine_profile({
        "name": name, "composition": composition, "unit": unit,
        "is_discontinued": discontinued,
    })


@pytest.mark.parametrize("candidate_name,candidate_comp,candidate_unit,eligible", [
    ("Other 4 Tablet", "Ondansetron (4mg)", "strip of 10 tablets", True),
    ("Zofer 8mg Tablet", "Ondansetron (8mg)", "strip of 10 tablets", False),
    ("Zofer Injection", "Ondansetron (4mg)", "vial of 1 Injection", False),
    ("Zofer 4 SR Tablet", "Ondansetron (4mg)", "strip of 10 tablet sr", False),
    ("Zofer 4 DT Tablet", "Ondansetron (4mg)", "strip of 10 tablet dt", False),
])
def test_strict_profile_matching(candidate_name, candidate_comp, candidate_unit, eligible):
    selected = profile("Zofer 4mg Tablet", "Ondansetron (4mg)", "strip of 10 tablets")
    result = compare_medicine_profiles(selected, profile(candidate_name, candidate_comp, candidate_unit))
    assert result["eligible"] is eligible


def test_reversed_ingredient_order_is_eligible():
    selected = profile("Oflazest OZ Tablet", "Ofloxacin (200mg) + Ornidazole (500mg)", "strip of 10 tablets")
    candidate = profile("Other OZ Tablet", "Ornidazole (500mg) + Ofloxacin (200mg)", "strip of 10 tablets")
    assert build_composition_key(selected["composition"]) == build_composition_key(candidate["composition"])
    assert compare_medicine_profiles(selected, candidate)["eligible"] is True


def test_missing_combination_ingredient_is_blocked():
    selected = profile("Oflazest OZ Tablet", "Ofloxacin (200mg) + Ornidazole (500mg)", "strip of 10 tablets")
    candidate = profile("Oflazest 200mg Tablet", "Ofloxacin (200mg)", "strip of 10 tablets")
    assert compare_medicine_profiles(selected, candidate)["eligible"] is False


def test_liquid_strength_does_not_match_tablet():
    tablet = profile("Azithromycin 500 Tablet", "Azithromycin (500mg)", "strip of 3 tablets")
    liquid = profile("Azithromycin Liquid", "Azithromycin (200mg/5ml)", "bottle of 15 ml suspension")
    assert compare_medicine_profiles(tablet, liquid)["eligible"] is False


def test_discontinued_is_a_query_level_hard_block():
    selected = profile("Zofer 4mg Tablet", "Ondansetron (4mg)", "strip of 10 tablets")
    candidate = profile("Other Tablet", "Ondansetron (4mg)", "strip of 10 tablets", discontinued=1)
    result = compare_medicine_profiles(selected, candidate)
    assert result["eligible"] is False
    assert result["candidateActive"] is False


def test_missing_strength_requires_review_when_both_match():
    selected = profile("Brand A Tablet", "Paracetamol", "strip of 10 tablets")
    candidate = profile("Brand B Tablet", "Paracetamol", "strip of 10 tablets")
    result = compare_medicine_profiles(selected, candidate)
    assert result["eligible"] is True
    assert result["missingStrengthReviewRequired"] is True


@pytest.mark.parametrize("name,label", [
    ("Crocin Advance 500mg Tablet", "strip of 15 tablets"),
    ("Pain Rapid Tablet", "strip of 10 tablets"),
    ("Acme Paracetamol Tablet", "Optizorb coated tablet"),
    ("QuickGel Capsule", "strip of 10 capsules"),
])
def test_fast_absorption_formulation_variant_detection(name, label):
    assert detect_formulation_variant(name, label) == "fast_absorption"


def test_formulation_variant_mismatch_requires_review_but_does_not_block():
    selected = profile("Crocin Advance 500mg Tablet", "Paracetamol (500mg)", "strip of 15 tablets")
    candidate = profile("Paracetamol 500mg Tablet", "Paracetamol (500mg)", "strip of 10 tablets")
    result = compare_medicine_profiles(selected, candidate)
    assert result["eligible"] is True
    assert result["formulationMatch"] is False
    assert result["formulationReviewRequired"] is True
    assert "Release type differs" not in result["blockReasons"]
