"""Unit tests for concept-based need/skill matching."""

import pytest
from app.matching import score_match


@pytest.mark.parametrize(
    "need,description,skill,details",
    [
        ("Ride to church", "Need a ride each Sunday morning", "Driving", "Rides to appointments"),
        ("Lawn mowing", "Cannot push a mower", "Lawn care", None),
        ("Need someone to mow my grass", None, "Lawn mowing", None),
        ("Bread and homemade meals", "Recovering from surgery", "Baking", "Pies and cakes"),
        ("Computer help", "Printer will not connect", "Wi-Fi setup", "Routers and printers"),
        ("Dog walking", None, "Pet sitting", None),
        ("Babysitting", "Evening child care", "Child care", None),
        ("Spanish tutoring", None, "Tutoring", "Math and reading"),
    ],
)
def test_related_needs_and_skills_match(need, description, skill, details):
    assert score_match(need, description, skill, details) > 0


@pytest.mark.parametrize(
    "need,description,skill,details",
    [
        ("Ride to church", "Need a ride each Sunday morning", "Baking", "Bread, pies, and cakes for church events"),
        ("Computer repair", "Laptop is slow", "Carpentry", "Fence repair and shelves"),
        ("Plumbing repair", "Sink is leaking", "Auto repair", "Oil changes, brakes"),
        ("Spanish tutoring", "Learning Spanish for work", "Tech tutoring", "Smartphones and email"),
        ("Babysitting", "Evening child care", "Nursing care", "Blood pressure checks"),
        ("Piano lessons", None, "Gardening", "Vegetable beds"),
    ],
)
def test_unrelated_needs_and_skills_do_not_match(need, description, skill, details):
    assert score_match(need, description, skill, details) == 0


def test_single_stray_word_in_details_is_not_a_match():
    assert score_match("Church supper help", None, "Baking", "Cakes for church events") == 0


def test_two_detail_concepts_can_match_a_vaguely_named_skill():
    assert score_match("Fix leaking faucet", "Sink drain is slow", "Handyman", "Plumbing, faucets, and drains") > 0


def test_name_match_outranks_detail_only_match():
    named = score_match("Lawn mowing", None, "Lawn mowing", None)
    detail = score_match("Lawn mowing and leaf raking", None, "Outdoor chores", "Mowing the grass and raking leaves")
    assert named > detail > 0
