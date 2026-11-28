"""A long Python file is written as a typed skeleton first, then one function at a time into its own place.

One shot of several hundred lines gets cut off near the end on a 7B model. Here every function replaces exactly the
syntax-tree span of its stub and the file must still parse afterwards, so nothing can be truncated in the middle.
"""

from __future__ import annotations

import ast
import re
import textwrap
from collections.abc import Awaitable, Callable

from prompt_loader import load_prompt

LONG_FILE_LINES = 250
_MANY_PARTS = 8
_ROUTE_RE = re.compile(r"\b(?:GET|POST|PUT|PATCH|DELETE)\s+/[\w/{}:.-]*")
_BLOCK_RE = re.compile(r"```[a-zA-Z0-9_+-]*\s*\n([\s\S]*?)\n```")

Generate = Callable[[str], Awaitable[str]]


def wanted(path: str, request: str) -> bool:
    """True when the request alone shows the file will be long: many separate endpoints belong to it."""
    name = path.rsplit("/", 1)[-1]
    return name in ("app.py", "main.py", "routes.py", "api.py") and len(set(_ROUTE_RE.findall(request))) >= _MANY_PARTS


def cut_off(path: str, code: str) -> bool:
    """A long file that stops parsing in its last lines was truncated by the token limit."""
    if not path.endswith(".py"):
        return False
    try:
        ast.parse(code)
    except SyntaxError as error:
        lines = code.rstrip().count("\n") + 1
        return lines >= LONG_FILE_LINES // 2 and (error.lineno or 0) >= lines - 5
    return False


def _body(answer: str) -> str:
    blocks = _BLOCK_RE.findall(answer)
    return (max(blocks, key=len) if blocks else answer).strip("\n") + "\n"


def _is_stub(node: ast.AST) -> bool:
    if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
        return False
    last = node.body[-1]
    return isinstance(last, ast.Raise) and "NotImplementedError" in ast.dump(last)


def stubs(code: str) -> list[tuple[str, int, int, int]]:
    """(qualified name, first line, last line, indent) of every unfilled function, 1-based lines including decorators."""
    found = []

    def visit(node: ast.AST, prefix: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                visit(child, f"{prefix}{child.name}.")
            elif _is_stub(child):
                start = min([child.lineno, *[d.lineno for d in child.decorator_list]])
                found.append((prefix + child.name, start, child.end_lineno or child.lineno, child.col_offset))

    visit(ast.parse(code), "")
    return found


def _replaced(code: str, span: tuple[int, int, int], answer: str, name: str) -> str:
    """The file with the stub swapped for the answer; unchanged when the answer is not that function, complete and parsable."""
    start, end, indent = span
    piece = textwrap.dedent(_body(answer))
    try:
        tree = ast.parse(piece)
    except SyntaxError:
        return code
    match = [n for n in tree.body if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef) and n.name == name.rsplit(".", 1)[-1]]
    if not match or _is_stub(match[0]):
        return code
    first = min([match[0].lineno, *[d.lineno for d in match[0].decorator_list]])
    part = "\n".join(piece.splitlines()[first - 1 : match[0].end_lineno])
    lines = code.splitlines()
    candidate = "\n".join([*lines[: start - 1], textwrap.indent(part, " " * indent), *lines[end:]]) + "\n"
    try:
        ast.parse(candidate)
    except SyntaxError:
        return code
    return candidate


async def write(request: str, generate: Generate, tries: int = 2) -> tuple[str, list[str]]:
    """(file text, names of functions that could not be filled). Raises ValueError when no parsable skeleton arrives."""
    code = ""
    for _attempt in range(tries):
        candidate = _body(await generate(f"{request}\n\n{load_prompt('skeleton_first.txt')}"))
        try:
            ast.parse(candidate)
        except SyntaxError:
            continue
        code = candidate
        break
    if not code:
        raise ValueError("ayrıştırılabilir iskelet üretilemedi")
    given_up: list[str] = []
    while todo := [s for s in stubs(code) if s[0] not in given_up]:
        name, start, end, indent = todo[0]
        ask = f"{load_prompt('skeleton_fill.txt')}\n\nİSTEK:\n{request}\n\nDOSYA:\n{code}\n\nTAMAMLANACAK FONKSİYON: {name}"
        for _attempt in range(tries):
            filled = _replaced(code, (start, end, indent), await generate(ask), name)
            if filled != code:
                code = filled
                break
        else:
            given_up.append(name)
    return code, given_up
