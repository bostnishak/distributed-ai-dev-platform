"""Flow diagrams: validated model output, loops and skipped layers are laid out, arrowheads are drawn."""

from __future__ import annotations

import pytest

import flowchart_studio as fs

pytestmark = pytest.mark.unit
PAL = {"bg1": "#fff", "bg2": "#eef", "primary": "#33c", "accent": "#69f", "text": "#012", "muted": "#456"}
RAW = {
    "title": "Giriş",
    "steps": [{"id": "a", "type": "start", "label": "Başla"}, {"id": "b", "type": "process", "label": "Şifre gir"}, {"id": "c", "type": "decision", "label": "Doğru mu?"}, {"id": "d", "type": "end", "label": "Bitir"}],
    "edges": [{"from": "a", "to": "b"}, {"from": "b", "to": "c"}, {"from": "c", "to": "d", "label": "Evet"}, {"from": "c", "to": "b", "label": "Hayır"}],
}


def test_flow_request_detection():
    assert fs.is_flow_request("Kullanıcı girişi akışını gösteren bir akış diyagramı çiz")
    assert not fs.is_flow_request("sistem mimarisi diyagramı çiz")


def test_clean_rejects_unusable_and_keeps_valid():
    assert fs.clean({"steps": []}) is None
    assert fs.clean(RAW)["steps"][2]["type"] == "decision"


def test_loop_does_not_break_layers_and_svg_has_arrowheads():
    spec = fs.clean(RAW)
    depth = fs._layers(spec)
    assert depth["a"] < depth["b"] < depth["c"] < depth["d"]
    svg = fs.render(spec, PAL)
    assert svg.count("<polygon") >= 4 and "Hayır" in svg and "Evet" in svg
