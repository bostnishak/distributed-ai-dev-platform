"""Generated code is executed with its tests; placeholder imports are repaired before running."""

from __future__ import annotations

import pytest

import code_verify as cv

pytestmark = pytest.mark.unit

ANSWER = """Kod:
```python
def add(a, b):
    return a + b
```
Test:
```python
from your_module_name_here import add

def test_add():
    assert add(1, 2) == 3
```
"""


def test_blocks_are_split_into_code_and_tests():
    impls, tests = cv.split_blocks(ANSWER)
    assert len(impls) == 1 and "def add" in impls[0] and len(tests) == 1 and "def test_add" in tests[0]


def test_placeholder_import_is_rewritten(tmp_path):
    impls, tests = cv.split_blocks(ANSWER)
    cv.build_project(impls, tests, tmp_path)
    assert (tmp_path / "solution.py").exists()
    assert "from solution import add" in (tmp_path / "test_generated.py").read_text(encoding="utf-8")


def test_real_module_name_is_kept(tmp_path):
    cv.build_project(["x = 1"], ["from cache import x\n\ndef test_x():\n    assert x == 1"], tmp_path)
    assert (tmp_path / "cache.py").exists()


def test_no_tests_means_no_note():
    import asyncio

    assert asyncio.run(cv.verify("x", "```python\nprint(1)\n```")) == ""
