"""Small coding tasks whose answers are decided by running them, never by a model's opinion."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import code_verify
import workspace_builder as wb


@dataclass(frozen=True)
class Task:
    name: str
    spec: str
    checks: str  # pytest source importing from solution


def _task(name: str, spec: str, *asserts: str) -> Task:
    body = "\n".join(f"    {line}" for line in asserts)
    return Task(name, spec, f"from solution import {name}\n\n\ndef test_{name}():\n{body}\n")


TASKS = (
    _task("parse_duration", "parse_duration(text) -> int: '1h 30m 15s' biçimini saniyeye çevir; boş metin 0.", "assert parse_duration('1h 30m 15s') == 5415", "assert parse_duration('45s') == 45", "assert parse_duration('') == 0"),
    _task("merge_ranges", "merge_ranges(list_of_pairs) -> list: çakışan ya da bitişik kapalı aralıkları birleştirip sıralı döndür.", "assert merge_ranges([[5, 6], [1, 3], [3, 4]]) == [[1, 4], [5, 6]]", "assert merge_ranges([]) == []"),
    _task("tr_lower", "tr_lower(text) -> str: Türkçe küçük harfe çevir (I -> ı, İ -> i).", "assert tr_lower('IŞIK İZMİR') == 'ışık izmir'", "assert tr_lower('abc') == 'abc'"),
    _task("balanced", "balanced(text) -> bool: (), [], {} parantezleri doğru iç içe mi.", "assert balanced('a(b[c]{d})')", "assert not balanced('([)]')", "assert not balanced('(')"),
    _task("roman", "roman(n) -> str: 1..3999 arası sayıyı Roma rakamına çevir; aralık dışı ValueError.", "assert roman(1994) == 'MCMXCIV'", "assert roman(4) == 'IV'", "import pytest", "pytest.raises(ValueError, roman, 0)"),
    _task("group_anagrams", "group_anagrams(words) -> list[list[str]]: anagramları grupla; her grup sıralı, gruplar ilk elemana göre sıralı.", "assert group_anagrams(['eat', 'tan', 'ate', 'nat', 'bat']) == [['ate', 'eat'], ['bat'], ['nat', 'tan']]"),
    _task("moving_average", "moving_average(values, k) -> list[float]: k genişliğinde kayan ortalama; k <= 0 ya da k > len ise ValueError.", "assert moving_average([1, 2, 3, 4], 2) == [1.5, 2.5, 3.5]", "import pytest", "pytest.raises(ValueError, moving_average, [1], 2)"),
    _task("flatten", "flatten(nested) -> list: her derinlikteki iç içe listeleri düzleştir; metinler bölünmez.", "assert flatten([1, [2, [3, ['ab']]], []]) == [1, 2, 3, 'ab']"),
)
SYSTEM = "Python 3.12. Yalnız tek bir ```python bloğu döndür: istenen fonksiyonun tamamı. Test ya da açıklama yazma."


async def solve(model: str, task: Task, hint: str = "") -> str:
    answer = await wb._ollama_generate(model, SYSTEM, task.spec + hint, num_predict=1200, temperature=0.1)
    impls, _tests = code_verify.split_blocks(answer)
    return "\n\n".join(impls) or wb._strip_code_fences(answer)


async def passes(code: str, checks: str) -> tuple[bool, str]:
    return await asyncio.to_thread(code_verify.run_tests, [code], [checks])


async def score(model: str, tasks: tuple[Task, ...] = TASKS) -> dict[str, bool]:
    results = {}
    for task in tasks:
        results[task.name] = (await passes(await solve(model, task), task.checks))[0]
    return results
