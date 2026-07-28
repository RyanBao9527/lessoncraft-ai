"""Unicode-aware deterministic matching for course terms and aliases."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable


def normalize_term(value: str) -> str:
    """Normalize spelling differences without changing the authored text."""

    normalized = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"[\s\-_/·、，,。；;：:（）()]+", "", normalized)


def contains_term(text: str, term: str) -> bool:
    """Match identifiers by token boundary and Chinese phrases compactly."""

    normalized_text = unicodedata.normalize("NFKC", text).casefold()
    normalized_term = unicodedata.normalize("NFKC", term).casefold().strip()
    if not normalized_term:
        return False
    if re.fullmatch(r"[a-z_][a-z0-9_]*", normalized_term):
        return bool(
            re.search(
                rf"(?<![a-z0-9_]){re.escape(normalized_term)}(?![a-z0-9_])",
                normalized_text,
            )
        )
    return normalize_term(normalized_term) in normalize_term(normalized_text)


def any_term_in(text: str, variants: Iterable[str]) -> bool:
    """Return whether any canonical spelling or alias occurs in text."""

    return any(contains_term(text, item) for item in variants if item)


def build_alias_groups(
    items: Iterable[tuple[str, Iterable[str]]],
) -> dict[str, tuple[str, ...]]:
    """Index every canonical term and alias to its complete spelling group."""

    groups: dict[str, tuple[str, ...]] = {}
    for term, aliases in items:
        variants = tuple(dict.fromkeys([term, *aliases]))
        for variant in variants:
            groups[normalize_term(variant)] = variants
    return groups


def variants_for(
    term: str, alias_groups: dict[str, tuple[str, ...]]
) -> tuple[str, ...]:
    """Return the alias group for a scope term, falling back to itself."""

    direct = alias_groups.get(normalize_term(term))
    if direct:
        return direct
    matching = [
        variants
        for key, variants in alias_groups.items()
        if key and (
            key in normalize_term(term)
            or normalize_term(term) in key
        )
    ]
    return matching[0] if matching else (term,)
