"""Several agents on one project at once, each in its own git worktree, merged by meaning.

"paralel ajanlar: <task one> ; <task two>" copies the project into a temporary git repository, gives every task a
branch and worktree, lets them edit side by side, then merges the branches symbol by symbol. A real clash goes to a
resolver agent. The result replaces the project only when it passes the project's tests in the sandbox; each task
becomes one conventional commit in the changelog.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import tempfile
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from fastapi.responses import StreamingResponse

import chat_stream
import dag
import merge3
import process_utils
import revise_chat
import run_control
import semantic_merge
import workspace_builder as wb
import workspace_docker
from workspace_batches import apply_edit

_TRIGGER_RE = re.compile(r"^\s*(?:paralel\s+ajanlar(?:la)?|parallel\s+agents)\s*:\s*(?P<body>.+)$", re.IGNORECASE | re.DOTALL)
_SPLIT_RE = re.compile(r"\s*(?:;|\n+)\s*")
_NUMBER_RE = re.compile(r"^(?:[-*]|\d+[.)])\s*")
_TEXT = (".py", ".js", ".ts", ".html", ".css", ".json", ".md", ".txt", ".sql", ".yml", ".yaml", ".toml")
MAX_TASKS = 4


def tasks_of(prompt: str) -> list[str]:
    match = _TRIGGER_RE.match(prompt)
    if not match:
        return []
    tasks = [_NUMBER_RE.sub("", t).strip() for t in _SPLIT_RE.split(match["body"])]
    return [t for t in tasks if len(t) > 5][:MAX_TASKS]


def commit_type(task: str) -> str:
    lowered = task.casefold()
    for kind, words in (("fix", ("düzelt", "hata", "fix", "bug")), ("test", ("test",)), ("refactor", ("yeniden düzenle", "refactor", "sadeleştir"))):
        if any(w in lowered for w in words):
            return kind
    return "feat"


def git(cwd: Path, *args: str) -> str:
    exe = shutil.which("git")
    if not exe:
        raise RuntimeError("git bulunamadı")
    env = {**os.environ, "GIT_AUTHOR_NAME": "platform", "GIT_AUTHOR_EMAIL": "platform@localhost", "GIT_COMMITTER_NAME": "platform", "GIT_COMMITTER_EMAIL": "platform@localhost"}
    done = process_utils.run_process([exe, "-c", "core.autocrlf=false", "-c", "core.hooksPath=", *args], cwd=cwd, env=env, timeout_s=60, max_output_chars=5_000_000)
    if done.returncode != 0:
        raise RuntimeError(f"git {args[0]}: {done.stderr.strip()[:300]}")
    return done.stdout


def make_repo(ws_dir: Path, root: Path) -> Path:
    repo = root / "repo"
    repo.mkdir(parents=True)
    for rel in wb.list_relative_files(ws_dir):
        if rel.endswith(_TEXT):
            (repo / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ws_dir / rel, repo / rel)
    git(repo, "init", "-q")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "--allow-empty", "-m", "chore: başlangıç")
    return repo


def add_worktree(repo: Path, index: int, task: str) -> tuple[Path, str]:
    slug = re.sub(r"[^a-z0-9]+", "-", wb.slugify(task).lower())[:30].strip("-") or "gorev"
    branch, path = f"agent/{index}-{slug}", repo.parent / f"agent-{index}"
    git(repo, "worktree", "add", "-q", "-b", branch, str(path))
    return path, branch


def _read(repo: Path, ref: str, rel: str) -> str:
    try:
        return git(repo, "show", f"{ref}:{rel}")
    except RuntimeError:
        return ""


def merge_branch(repo: Path, branch: str) -> list[semantic_merge.Conflict]:
    """Merge one agent branch into the main checkout, file by file and symbol by symbol; returns open conflicts."""
    base_ref = git(repo, "merge-base", "HEAD", branch).strip()
    open_conflicts: list[semantic_merge.Conflict] = []
    for rel in git(repo, "diff", "--name-only", base_ref, branch).split("\n"):
        if not rel:
            continue
        base, ours, theirs = _read(repo, base_ref, rel), _read(repo, "HEAD", rel), _read(repo, branch, rel)
        if rel.endswith(".py") and base and ours and theirs:
            try:
                merged, conflicts = semantic_merge.merge(base, ours, theirs)
            except SyntaxError:
                merged, lines = merge3.merge(base, theirs, ours, rel)
                conflicts = [semantic_merge.Conflict(f"satır {n}", "", "", "") for n in lines]
        else:
            merged, lines = merge3.merge(base, theirs, ours, rel) if base else (theirs, [])
            conflicts = [semantic_merge.Conflict(f"satır {n}", "", "", "") for n in lines]
        open_conflicts += [semantic_merge.Conflict(f"{rel}::{c.name}", c.base, c.ours, c.theirs) for c in conflicts]
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (repo / rel).write_text(merged, encoding="utf-8", newline="\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "--allow-empty", "-m", f"merge: {branch}")
    return open_conflicts


async def resolve(repo: Path, conflict: semantic_merge.Conflict, model: str) -> bool:
    """A resolver agent writes the one symbol both sides changed; accepted only when the file still parses."""
    rel, name = conflict.name.split("::", 1)
    if not rel.endswith(".py") or name.startswith("satır") or not conflict.ours or not conflict.theirs:
        return False
    ask = (f"İki ajan aynı Python tanımını farklı değiştirdi. İKİ değişikliği de koruyan tek bir tanım yaz.\n\nÖNCEKİ:\n{conflict.base}\n\n"
           f"BİRİNCİ:\n{conflict.ours}\n\nİKİNCİ:\n{conflict.theirs}\n\nSADECE birleşik tanımın Python kodunu döndür.")
    code = wb._strip_code_fences(await wb._ollama_generate(model, "Sadece Python kodu döndür.", ask, num_predict=1500, temperature=0.1))
    path = repo / rel
    try:
        merged = semantic_merge.replace_symbol(path.read_text(encoding="utf-8"), name, code)
    except SyntaxError:
        return False
    path.write_text(merged, encoding="utf-8", newline="\n")
    git(repo, "commit", "-q", "-am", f"fix: {name} çakışması çözüldü")
    return True


def _files(worktree: Path) -> list[str]:
    return [p.relative_to(worktree).as_posix() for p in sorted(worktree.rglob("*")) if p.is_file() and ".git" not in p.parts]


async def _targets(worktree: Path, task: str, model: str) -> list[dict[str, str]]:
    files = _files(worktree)
    listing = "\n".join(f"- {f}" for f in files)
    raw = await wb._ollama_generate(model, "Sadece geçerli JSON döndür. En fazla 3 dosya seç.",
                                    f'Dosyalar:\n{listing}\n\nGörev: {task}\nDeğişecek dosyalar: {{"files": [{{"path": "...", "purpose": "..."}}]}}', num_predict=400, temperature=0.1)
    plan = wb._extract_json_obj(raw) or {}
    chosen = [f for f in plan.get("files", []) if isinstance(f, dict) and wb._is_safe_rel_path(str(f.get("path", "")))]
    return chosen[:3] or [{"path": files[0], "purpose": task}]


async def agent_edit(worktree: Path, task: str, model: str) -> list[str]:
    """One agent's work inside its own worktree; returns the files it wrote."""
    written = []
    for spec in await _targets(worktree, task, model):
        target = worktree / spec["path"]
        current = target.read_text(encoding="utf-8") if target.is_file() else ""
        prompt = (f"Görev: {task}\nHedef dosya: `{spec['path']}`\n\nMevcut içerik:\n```\n{current[:24000]}\n```\n\n"
                  "Bu dosyanın EKSİKSİZ güncel içeriğini yaz. Görevle ilgisi olmayan hiçbir şeyi değiştirme.")
        await apply_edit(wb._generate_and_write_file, (worktree, model, prompt), {"path": spec["path"], "purpose": task}, current)
        written.append(spec["path"])
    return written


def changelog(tasks: list[str], branches: list[str], repo: Path) -> str:
    lines = []
    for task, branch in zip(tasks, branches, strict=True):
        files = git(repo, "diff", "--name-only", f"{branch}~1", branch).split()
        lines.append(f"- `{commit_type(task)}: {task[:80]}` ({', '.join(files) or 'değişiklik yok'}; dal `{branch}`)")
    return "\n".join(lines)


def _apply(repo: Path, ws_dir: Path, label: str) -> None:
    for rel in git(repo, "ls-files").split("\n"):
        if rel:
            (ws_dir / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(repo / rel, ws_dir / rel)
    wb.create_snapshot(ws_dir, label[:60])
    meta = wb.load_workspace_meta(ws_dir)
    meta["versions"] = wb.list_snapshots(ws_dir)
    wb.save_workspace_meta(ws_dir, meta)


async def _stream(ws_id: str, tasks: list[str]) -> AsyncIterator[Any]:
    ws_dir = wb.safe_workspace_dir(ws_id)
    model = await wb.pick_coder_model(None)
    with tempfile.TemporaryDirectory(prefix="cm6453_swarm_", ignore_cleanup_errors=True) as tmp:
        repo = make_repo(ws_dir, Path(tmp))
        trees = [add_worktree(repo, i, task) for i, task in enumerate(tasks, 1)]
        yield f"{len(tasks)} ajan ayrı git çalışma kopyalarında başlıyor: " + ", ".join(f"`{b}`" for _p, b in trees) + "\n\n"

        def work_for(path: Path, task: str) -> Any:
            async def work(record: dict[str, Any]) -> str:
                wanted = task + "".join(f"\nEK TALİMAT: {n}" for n in record.get("notes", []))
                files = await agent_edit(path, wanted, model)
                git(path, "add", "-A")
                git(path, "commit", "-q", "--allow-empty", "-m", f"{commit_type(task)}: {task[:60]}")
                return json.dumps(files)

            return work

        run = run_control.start(f"paralel ajanlar: {'; '.join(tasks)}", ws_id)
        nodes = [dag.Node(branch, work_for(path, task), model=model, title=branch, purpose=task) for (path, branch), task in zip(trees, tasks, strict=True)]
        async for kind, node, result in dag.execute(run, nodes, max(1, int(os.environ.get("WS_PARALLEL", "2")))):
            if kind == "done" and node:
                yield f"- `{node.id}` bitti: {', '.join(json.loads(result))}\n"
        branches = [b for _p, b in trees]
        log = changelog(tasks, branches, repo)
        unresolved = []
        for branch in branches:
            for conflict in merge_branch(repo, branch):
                solved = await resolve(repo, conflict, model)
                yield f"- Çakışma `{conflict.name}`: {'çözümleyici ajan birleştirdi' if solved else 'çözülemedi'}\n"
                if not solved:
                    unresolved.append(conflict.name)
        failure = ""
        if any(p.name.startswith("test_") for p in repo.rglob("*.py")) and workspace_docker.available():
            failure = await asyncio.to_thread(workspace_docker.run_tests, repo, [])
        if unresolved or failure:
            yield f"\nProje DEĞİŞTİRİLMEDİ: {'çözülmeyen çakışma: ' + ', '.join(unresolved) if unresolved else 'birleşik kodda test başarısız: ' + failure}\n"
            return
        _apply(repo, ws_dir, "Paralel ajanlar: " + "; ".join(tasks))
        yield f"\nBirleştirildi ve yeni sürüm kaydedildi.\n\n{log}\n"
        yield {"type": "run", "run_id": run.id}


def fastpath(prompt: str, history: str) -> StreamingResponse | None:
    tasks = tasks_of(prompt)
    if len(tasks) < 2:
        return None
    ws_id = revise_chat.last_workspace_id(history) or next((str(w.get("id", "")) for w in wb.list_workspaces()), "")
    return chat_stream.reply(_stream(ws_id, tasks), "paralel-ajanlar", "proje") if ws_id else None
