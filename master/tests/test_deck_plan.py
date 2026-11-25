"""Deck layout plan: variety without data layouts when the request has no numbers, and plan application."""

from __future__ import annotations

import itertools

import pytest

import deck_plan

pytestmark = pytest.mark.unit


def test_plan_has_no_data_layouts_without_numbers_and_no_repeats():
    plan = deck_plan.layout_plan(7, "KOBİ siber güvenlik farkındalığı sunumu")
    assert len(plan) == 7 and plan[-1] == "closing"
    assert "kpi_grid" not in plan and "chart" not in plan
    assert all(a != b for a, b in itertools.pairwise(plan))


def test_plan_uses_kpi_and_chart_when_request_gives_numbers():
    plan = deck_plan.layout_plan(6, "Ürün 349 TL maliyet 140 TL satış 12000 30000 65000 grafik")
    assert "kpi_grid" in plan and "chart" in plan


def test_apply_moves_fitting_bullet_slides_only():
    slides = [{"layout": "bullets", "bullets": ["a", "b", "c"]}, {"layout": "bullets", "bullets": ["a"]}]
    out = deck_plan.apply(slides, ["steps", "steps"])
    assert out[0]["layout"] == "steps" and out[1]["layout"] == "bullets"
