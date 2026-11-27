"""The browser gate must reject a page whose Add button leaves the screen unchanged (needs Docker + jsdom)."""

import pytest

import workspace_docker
import workspace_web

pytestmark = pytest.mark.unit

_PAGE = """<html><body><input id="n" type="text"><button id="a">Add</button><button id="all">All</button><ul id="list"></ul><script>
const items = [];
function render() { const ul = document.getElementById('list'); ul.textContent = ''; items.forEach((i) => { const li = document.createElement('li'); li.textContent = i; ul.appendChild(li); }); }
document.getElementById('a').addEventListener('click', () => { items.push(document.getElementById('n').value); RENDER });
</script></body></html>"""


@pytest.fixture
def probe(tmp_path):
    if not workspace_docker.available():
        pytest.skip("Docker yok")

    def run(page):
        (tmp_path / "index.html").write_text(page, encoding="utf-8")
        result = workspace_web.probe(tmp_path)
        if result is None:
            pytest.skip("jsdom kurulamadı")
        return " ".join(result["errors"])

    return run


def test_dead_add_button_is_rejected(probe):
    assert "Ekleme calismiyor" in probe(_PAGE.replace("RENDER", ""))


def test_working_add_button_passes(probe):
    assert probe(_PAGE.replace("RENDER", "render();")) == ""
