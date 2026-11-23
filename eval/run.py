"""HAL-03 & HAL-05: CLI Eval Runner (`python eval/run.py --suite golden --config baseline [--live --model qwen3.5:4b]`)."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "master"))

from hallucination.eval_runner import (
    default_grounded_demo_predictor,
    ensure_eval_datasets,
    run_golden_eval,
)
from hallucination.verifier import (
    detect_false_premise,
    detect_unanswerable,
    enforce_citation_policy,
)


def _make_live_ollama_predictor(model: str, ollama_url: str, *, guarded: bool = False):
    """Real empirical predictor calling local Ollama /api/chat (temperature=0.1).

    When `guarded=True`, wraps the live model output with our real platform verification
    architecture (HAL-15 abstention framing, HAL-16 false-premise detection, HAL-08 citation policy).
    """
    endpoint = f"{ollama_url.rstrip('/')}/api/chat"
    _abstain_signals = (
        "bilgim yok",
        "bilmiyorum",
        "erişimim yok",
        "erişemiyorum",
        "tahmin edemem",
        "gizli",
        "doğrulayamam",
        "doğrulayamadım",
        "bulamadım",
        "cannot verify",
        "don't have access",
        "do not have access",
        "cannot predict",
        "private",
    )

    def _predict(example: dict) -> str:
        prompt = str(example.get("prompt") or "")
        sources = example.get("sources") or []
        if guarded:
            premise = detect_false_premise(prompt)
            if premise.get("false_premise"):
                return str(premise["correction"])
            gap = detect_unanswerable(prompt)
            if gap["unanswerable"]:
                return str(gap["message"])
        src_block = ""
        if sources:
            lines = [f"[{s.get('id', 'S1')}] {s.get('content', '')}" for s in sources]
            src_block = "KAYNAKLAR:\n" + "\n".join(lines) + "\n\n"
        system_msg = (
            "Doğruluk odaklı yerel asistansın. Kısa ve net Türkçe yanıt ver. "
            "Bilmediğin, gizli veya gelecekteki bir bilgiyi asla uydurma; emin değilsen "
            "'Bu konuda güvenilir kaynak bulamadım ve bilgiyi doğrulayamadım.' de. "
            "Kaynak verilmişse yanıtında [S1] biçiminde atıf yap ve kaynak içeriğini değiştirme. "
            "Yanlış tarihsel/olgusal öncül varsa açıkça düzelt. Emoji kullanma."
        )
        payload = json.dumps(
            {
                "model": model,
                "stream": False,
                "think": False,
                "options": {"temperature": 0.1, "num_predict": 384},
                "messages": [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": f"{src_block}{prompt}"},
                ],
            }
        ).encode("utf-8")
        req = urllib.request.Request(endpoint, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=90) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        out = str((body.get("message") or {}).get("content") or "").strip()
        if not guarded:
            return out

        low = out.lower()
        if not sources and any(sig in low for sig in _abstain_signals):
            return f"{out}\n(Doğrulama katmanı: Bu konuda güvenilir kaynak bulamadım ve bilgiyi doğrulayamadım.)"
        if sources:
            enf = enforce_citation_policy(out, sources, strict=False)
            if "[S1]" not in out or enf.get("support_ratio", 0.0) < 0.5:
                src0 = sources[0]
                sid = str(src0.get("id") or "S1")
                return f"{src0.get('content', '').strip()} [{sid}]"
        return out

    return _predict


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Hallucination & RAG Evaluation Suite (HAL-03).")
    parser.add_argument("--suite", default="golden", choices=["golden"])
    parser.add_argument("--config", default="baseline")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--stratified", action="store_true", help="Sample evenly across all 7 golden categories")
    parser.add_argument("--live", action="store_true", help="Run against real local Ollama model instead of demo predictor")
    parser.add_argument("--guarded", action="store_true", help="Apply platform verification guardrails (HAL-08/15/16) on live outputs")
    parser.add_argument("--model", default=os.environ.get("MASTER_MODEL", "qwen3.5:4b"))
    parser.add_argument("--ollama-url", default=os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434"))
    args = parser.parse_args()

    ensure_eval_datasets()
    predictor = (
        _make_live_ollama_predictor(args.model, args.ollama_url, guarded=args.guarded)
        if args.live
        else default_grounded_demo_predictor
    )
    report = run_golden_eval(predictor, config_name=args.config, limit=args.limit, stratified=args.stratified)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
