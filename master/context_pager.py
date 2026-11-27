"""The context window as RAM, older turns as disk: pages are brought in when the question needs them.

Turns that no longer fit the history window are grouped into pages. `page_in` returns the ones that match the
question (rare words count more), within a character budget; pinned rules are charged first and are never evicted,
the lowest-scoring page goes first. `stale` pages — an old value the user later corrected — are marked as such.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

_WORD_RE = re.compile(r"\w{3,}")
_CORRECTION_RE = re.compile(r"\b(?:artık|yerine|değiştirdim|güncelledim|düzeltme|instead|no longer|changed)\b", re.IGNORECASE)
BUDGET = 3000


def _words(text: str) -> set[str]:
    return {w[:5] for w in _WORD_RE.findall(text.casefold())}


@dataclass
class Page:
    number: int
    text: str
    words: set[str] = field(default_factory=set)
    pinned: bool = False
    stale: bool = False


class ContextPager:
    def __init__(self, budget: int = BUDGET) -> None:
        self.budget = budget
        self.disk: list[Page] = []
        self.loaded: dict[int, float] = {}

    def page_out(self, text: str, pinned: bool = False) -> Page:
        page = Page(len(self.disk) + 1, text, _words(text), pinned)
        if _CORRECTION_RE.search(text):  # a later correction makes earlier pages about the same thing stale
            for old in self.disk:
                if not old.pinned and len(old.words & page.words) >= 2:
                    old.stale = True
        self.disk.append(page)
        return page

    def pin(self, number: int) -> None:
        self.disk[number - 1].pinned = True

    def score(self, query: str) -> dict[int, float]:
        wanted = _words(query)
        count = len(self.disk) or 1
        rarity = {w: math.log(1 + count / (1 + sum(w in p.words for p in self.disk))) for w in wanted}
        return {p.number: sum(rarity[w] for w in wanted & p.words) for p in self.disk}

    def evict(self) -> list[int]:
        """Drop the weakest unpinned pages until the loaded set fits; returns their numbers."""
        gone = []
        while sum(len(self.disk[n - 1].text) for n in self.loaded) > self.budget:
            victims = [n for n in self.loaded if not self.disk[n - 1].pinned]
            if not victims:
                break
            weakest = min(victims, key=lambda n: (not self.disk[n - 1].stale, self.loaded[n], n))
            del self.loaded[weakest]
            gone.append(weakest)
        return gone

    def page_in(self, query: str, limit: int = 4) -> list[Page]:
        scores = self.score(query)
        matches = sorted((p for p in self.disk if scores[p.number] > 0 and not p.stale), key=lambda p: (-scores[p.number], -p.number))[:limit]
        self.loaded = {p.number: float("inf") for p in self.disk if p.pinned} | {p.number: scores[p.number] for p in matches}
        self.evict()
        return [self.disk[n - 1] for n in sorted(self.loaded)]


def recall(items: list, window: int, query: str, budget: int = BUDGET) -> str:
    """A note with the earlier exchanges the current question is about ('' when none of them match)."""
    pager = ContextPager(budget)
    older = [i for i in items[:-window] if isinstance(i, dict) and i.get("text")]
    exchange: list[str] = []
    for item in older:
        if item.get("role") == "user" and exchange:
            pager.page_out("\n".join(exchange))
            exchange = []
        who = "Kullanıcı" if item.get("role") == "user" else "Yanıt"
        exchange.append(f"{who}: {str(item['text'])[:700]}")
    if exchange:
        pager.page_out("\n".join(exchange))
    pages = pager.page_in(query)
    if not pages:
        return ""
    body = "\n---\n".join(p.text for p in pages)
    return f"BU SOHBETİN DAHA ÖNCEKİ KISMINDAN SORUYLA İLGİLİ BÖLÜMLER (geçerli bilgi, gerekiyorsa bundan yanıtla):\n{body}"
