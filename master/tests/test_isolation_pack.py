"""Windows Job Object limits, WASM fuel and the training export."""

import json
import sys

import pytest

import config
import isolation
import training_pack

pytestmark = pytest.mark.unit
_ADD = '(module (func (export "add") (param i32 i32) (result i32) local.get 0 local.get 1 i32.add))'
_LOOP = '(module (func (export "spin") (result i32) (loop br 0) i32.const 0))'


@pytest.mark.skipif(sys.platform != "win32", reason="yalnız Windows")
def test_job_object_caps_memory_and_runs_normal_code():
    python = sys.executable
    ok = isolation.run_capped([python, "-c", "print(2+3)"])
    assert ok.returncode == 0 and ok.stdout.strip() == "5"
    greedy = isolation.run_capped([python, "-c", "x = bytearray(900*1024*1024); print('ayrıldı')"], memory_mb=300)
    assert greedy.returncode != 0 and "MemoryError" in greedy.stderr
    slow = isolation.run_capped([python, "-c", "while True: pass"], timeout_s=2)
    assert slow.returncode != 0


def test_wasm_runs_and_infinite_loop_runs_out_of_fuel():
    pytest.importorskip("wasmtime")
    assert isolation.run_wasm(_ADD, "add", 2, 3) == 5
    with pytest.raises(RuntimeError):
        isolation.run_wasm(_LOOP, "spin", fuel=10_000)


def test_export_pairs_verified_runs_and_redacts(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "platform.db")
    runs = []
    for name, passed in (("w-bad", False), ("w-good", True)):
        folder = tmp_path / "workspaces" / name
        folder.mkdir(parents=True)
        (folder / "app.py").write_text(f'API_KEY = "sk-{"a" * 30}"\nOK = {passed}\n', encoding="utf-8")
        runs.append({"request": "aynı istek", "workspace": name, "passed": passed})
    (tmp_path / "trajectories.jsonl").write_text("".join(json.dumps(r) + "\n" for r in runs), encoding="utf-8")
    assert training_pack.export(tmp_path / "out") == {"sft": 1, "dpo": 1}
    exported = (tmp_path / "out" / "sft_verified.jsonl").read_text(encoding="utf-8")
    assert "sk-aaaa" not in exported and "OK = True" in exported
    assert (tmp_path / "out" / "train_unsloth.py").is_file()
    with pytest.raises(ValueError, match="GGUF"):
        training_pack.modelfile(tmp_path / "out" / "train_unsloth.py")
