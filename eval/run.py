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


def _make_live_ollama_predictor(model: str, ollama_url: str):
    """Real empirical predictor calling local Ollama /api/chat (temperature=0.1) for honest baseline reporting."""
    endpoint = f"{ollama_url.rstrip('/')}/api/chat"

    def _predict(example: dict) -> str:
        sources = example.get("sources") or []
        src_block = ""
        if sources:
            lines = [f"[{s.get('id', 'S1')}] {s.get('content', '')}" for s in sources]
            src_block = "KAYNAKLAR:\n" + "\n".join(lines) + "\n\n"
        system_msg = (
            "Doğruluk odaklı yerel asistansın. Kısa ve net Türkçe yanıt ver. "
            "Bilmediğin veya kaynakta olmayan bilgiyi uydurma; emin değilsen 'Bu konuda güvenilir bilgim yok' de. "
            "Kaynak verilmişse [S1] biçiminde atıf yap. Yanlış tarihsel/olgusal öncül varsa düzelt. Emoji kullanma."
        )
        payload = json.dumps(
            {
                "model": model,
                "stream": False,
                "think": False,
                "options": {"temperature": 0.1, "num_predict": 384},
                "messages": [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": f"{src_block}{example['prompt']}"},
                ],
            }
        ).encode("utf-8")
        req = urllib.request.Request(endpoint, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=90) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        return str((body.get("message") or {}).get("content") or "").strip()

    return _predict


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Hallucination & RAG Evaluation Suite (HAL-03).")
    parser.add_argument("--suite", default="golden", choices=["golden"])
    parser.add_argument("--config", default="baseline")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--live", action="store_true", help="Run against real local Ollama model instead of demo predictor")
    parser.add_argument("--model", default=os.environ.get("MASTER_MODEL", "qwen3.5:4b"))
    parser.add_argument("--ollama-url", default=os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434"))
    args = parser.parse_args()

    ensure_eval_datasets()
    predictor = _make_live_ollama_predictor(args.model, args.ollama_url) if args.live else default_grounded_demo_predictor
    report = run_golden_eval(predictor, config_name=args.config, limit=args.limit)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
