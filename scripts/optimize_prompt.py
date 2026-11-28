"""Improve one agent prompt against the golden benchmark, and keep the change only if the benchmark says so.

Usage: python scripts/optimize_prompt.py <prompt file in master/prompts> <scenario> [<scenario> ...] [--repeats 3]
The local model proposes one added rule from the observed failures. The scenarios are run before and after; the rule
stays only when no scenario got worse and at least one got better, otherwise the file is restored byte for byte.
"""

from __future__ import annotations

import argparse
import random
import sys
from collections.abc import Callable
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
PROMPTS = ROOT / "master" / "prompts"
_MODEL = "qwen3.5:9b"
_ASK = ("Bir yapay zeka ajanının istem dosyası ve başarısız denemeleri veriliyor. İsteme eklenecek TEK bir kural cümlesi yaz: "
        "genel olsun, test sorusunun kendisini ya da cevabını içermesin. Yalnızca cümleyi yaz.")


def propose(prompt_text: str, failures: list[str]) -> str:
    sys.path.insert(0, str(ROOT / "master"))
    import config

    body = {"model": _MODEL, "stream": False, "think": False, "options": {"temperature": 0.3, "num_predict": 200},
            "messages": [{"role": "system", "content": _ASK}, {"role": "user", "content": f"İSTEM:\n{prompt_text}\n\nBAŞARISIZLIKLAR:\n" + "\n".join(failures)}]}
    resp = httpx.post(f"{config.OLLAMA_URL}/api/chat", json=body, timeout=300.0)
    resp.raise_for_status()
    return str(resp.json()["message"]["content"]).strip()


def measure(scenarios: list[Callable], repeats: int) -> tuple[list[int], list[str]]:
    """(passes per scenario, failure notes)."""
    passes, notes = [], []
    for scenario in scenarios:
        count = 0
        for attempt in range(repeats):
            try:
                scenario(random.Random(f"opt-{scenario.__name__}-{attempt}"))
                count += 1
            except AssertionError as exc:
                notes.append(f"{scenario.__name__}: {exc}"[:250])
        passes.append(count)
    return passes, notes


def usable(rule: str) -> bool:
    return 15 <= len(rule) <= 300 and "\n" not in rule and "```" not in rule


def optimize(path: Path, run: Callable[[], tuple[list[int], list[str]]], suggest: Callable[[str, list[str]], str]) -> str:
    """One round: measure, propose, measure again, keep or restore."""
    original = path.read_bytes()
    before, notes = run()
    if not notes:
        return "Bütün senaryolar zaten geçiyor; istem değiştirilmedi."
    rule = suggest(original.decode("utf-8"), notes).strip(" -\"")
    if not usable(rule):
        return "Model kullanılabilir bir kural öneremedi; istem değiştirilmedi."
    path.write_bytes(original.rstrip(b"\n") + b"\n- " + rule.encode("utf-8") + b"\n")
    try:
        after, _ = run()
    except BaseException:
        path.write_bytes(original)  # an interrupted measurement must not leave an unproven rule behind
        raise
    if sum(after) > sum(before) and all(new >= old for old, new in zip(before, after, strict=True)):
        return f"Kural eklendi ({sum(before)} -> {sum(after)} geçiş): {rule}"
    path.write_bytes(original)
    return f"Kural işe yaramadı ({sum(before)} -> {sum(after)}); istem eski haline döndürüldü: {rule}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("prompt")
    parser.add_argument("scenarios", nargs="+")
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    sys.path.insert(0, str(ROOT / "scripts"))
    import golden

    known = {f.__name__: f for table in (golden.FAST, golden.SLOW) for group in table.values() for f in group}
    role = PROMPTS / "v5" / f"{Path(args.prompt).stem}.md"  # agent roles live in v5/
    path = role if role.is_file() else PROMPTS / Path(args.prompt).name
    if not path.is_file() or any(s not in known for s in args.scenarios):
        print("İstem dosyası ya da senaryo bulunamadı. Senaryolar: " + ", ".join(sorted(known)))
        return 2
    chosen = [known[s] for s in args.scenarios]
    print(optimize(path, lambda: measure(chosen, args.repeats), propose))
    return 0


if __name__ == "__main__":
    sys.exit(main())
