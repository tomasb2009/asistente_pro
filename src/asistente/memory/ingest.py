"""
Detecta frases para guardar en memoria larga sin depender del intent del router.
"""

from __future__ import annotations

import re
import unicodedata

from asistente.memory.long_term import add_fact


def _fold(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn"
    )


_PATTERNS: list[tuple[re.Pattern[str], int]] = [
    (
        re.compile(
            r"(?:^|\s)(?:recuerda|recordá|recuerde)\s*:?\s*que\s+(.+?)(?:\.|$)",
            re.IGNORECASE | re.DOTALL,
        ),
        1,
    ),
    (
        re.compile(
            r"(?:^|\s)(?:no\s+olvides|no\s+olvidés)\s+que\s+(.+?)(?:\.|$)",
            re.IGNORECASE | re.DOTALL,
        ),
        1,
    ),
    (
        re.compile(
            r"(?:^|\s)(?:guarda|guardame|anota|anotá|memoriza|memorizá)\s*:?\s*(?:que\s+)?(.+?)(?:\.|$)",
            re.IGNORECASE | re.DOTALL,
        ),
        1,
    ),
    (
        re.compile(
            r"(?:^|\s)(?:importante|muy\s+importante)\s*:?\s*(.+?)(?:\.|$)",
            re.IGNORECASE | re.DOTALL,
        ),
        1,
    ),
    (
        re.compile(
            r"(?:^|\s)mi\s+nombre\s+es\s+(.+?)(?:\.|$)",
            re.IGNORECASE | re.DOTALL,
        ),
        1,
    ),
    (
        re.compile(
            r"(?:^|\s)me\s+llamo\s+(.+?)(?:\.|$)",
            re.IGNORECASE | re.DOTALL,
        ),
        1,
    ),
    (
        re.compile(
            r"(?:^|\s)(?:prefiero|me\s+gusta|odio|no\s+me\s+gusta)\s+(.+?)(?:\.|$)",
            re.IGNORECASE | re.DOTALL,
        ),
        1,
    ),
]


def try_ingest_from_message(message: str) -> bool:
    """
    Si el mensaje contiene un hecho explícito para recordar, lo guarda.
    Devuelve True si se almacenó algo.
    """
    raw = message.strip()
    if len(raw) < 4:
        return False

    folded = _fold(raw)

    for pat, group in _PATTERNS:
        m = pat.search(raw) or pat.search(folded)
        if not m:
            continue
        fact = m.group(group).strip()
        fact = re.sub(r"\s+", " ", fact)
        if len(fact) < 2 or len(fact) > 800:
            continue
        add_fact(fact)
        return True
    return False
