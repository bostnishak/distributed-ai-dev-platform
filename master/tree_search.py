"""Budgeted Monte Carlo tree search over candidate repairs.

A node is a version of the project's files, an edge is one proposed change, and the value of a node is the share of the
project's tests that pass on it, measured by running them. UCT decides which version to develop next, so a promising
partial fix is built on instead of every attempt starting from the broken original.
"""

from __future__ import annotations

import math
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

Files = dict[str, str]
Expand = Callable[[Files], Awaitable[list[Files]]]
Score = Callable[[Files], Awaitable[float]]


@dataclass
class Node:
    files: Files
    score: float
    parent: Node | None = None
    children: list[Node] = field(default_factory=list)
    visits: int = 0
    best: float = 0.0
    exhausted: bool = False

    def value(self, exploration: float) -> float:
        if not self.visits:
            return float("inf")
        spread = exploration * math.sqrt(math.log(max(self.parent.visits if self.parent else 1, 1)) / self.visits)
        return self.best + spread  # for repairs what matters is the best version found down a branch, not the average


def _select(root: Node, exploration: float) -> Node:
    """Walk down by UCT to a node that has not been expanded yet."""
    node = root
    while node.children and node.exhausted:
        node = max(node.children, key=lambda child: child.value(exploration))
    return node


def _backup(node: Node | None, score: float) -> None:
    while node:
        node.visits += 1
        node.best = max(node.best, score)
        node = node.parent


async def search(start: Files, expand: Expand, score: Score, budget: int = 6, exploration: float = 0.2) -> tuple[Files, float, int]:
    """(best files, their score, versions tried). Stops early when a version passes every test."""
    root = Node(start, await score(start))
    _backup(root, root.score)
    best = root
    seen = {tuple(sorted(start.items()))}
    tried = 0
    while tried < budget and best.score < 1.0:
        node = _select(root, exploration)
        if node.exhausted:  # a leaf that produced nothing new: count the visit so UCT moves elsewhere
            _backup(node, node.score)
            tried += 1
            continue
        node.exhausted = True
        for files in await expand(node.files):
            key = tuple(sorted(files.items()))
            if key in seen or tried >= budget:
                continue
            seen.add(key)
            tried += 1
            child = Node(files, await score(files), node)
            node.children.append(child)
            _backup(child, child.score)
            if child.score > best.score:
                best = child
            if best.score >= 1.0:
                break
        if not node.children:
            tried += 1
    return best.files, best.score, len(seen) - 1
