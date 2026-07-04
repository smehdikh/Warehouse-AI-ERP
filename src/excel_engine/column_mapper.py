"""Column mapper — maps raw column names to canonical field names using configurable rules."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class MappingResult:
    """Result of mapping a single column."""

    raw_name: str
    normalized_name: str
    mapped_field: str | None
    confidence: float
    strategy: str  # "exact", "normalized", "keyword", "none"


class ColumnMapper:
    """
    Map raw spreadsheet column headers to canonical field names.

    Mapping is done in priority order:

    1. **Exact match** against the provided ``mapping`` dict keys.
    2. **Normalised match** — both sides are lowercased, stripped, and
       have whitespace collapsed to underscores before comparison.
    3. **Keyword match** — checks whether any alias keyword from the dict
       appears as a whole word inside the normalised column name.

    The ``mapping`` dict maps *canonical field name* → *list of accepted aliases*.

    Example::

        mapping = {
            "product_id": ["id", "product id", "sku", "item_no"],
            "unit_price": ["price", "unit price", "cost"],
        }
    """

    def __init__(self, mapping: dict[str, list[str]] | None = None) -> None:
        self.mapping: dict[str, list[str]] = mapping or {}
        self._alias_index: dict[str, str] = {}  # alias → canonical
        self._rebuild_index()

    def set_mapping(self, mapping: dict[str, list[str]]) -> None:
        """Replace the active mapping and rebuild the internal index."""
        self.mapping = mapping
        self._rebuild_index()

    def map_columns(self, raw_names: list[str]) -> list[MappingResult]:
        """
        Map a list of raw column names.

        Args:
            raw_names: Column headers as read from the header row.

        Returns:
            A :class:`MappingResult` for every input name, in the same order.
        """
        return [self._map_one(name) for name in raw_names]

    def _map_one(self, raw_name: str) -> MappingResult:
        norm = self._normalize(raw_name)

        # 1. Exact match
        if raw_name in self._alias_index:
            return MappingResult(
                raw_name=raw_name,
                normalized_name=norm,
                mapped_field=self._alias_index[raw_name],
                confidence=1.0,
                strategy="exact",
            )

        # 2. Normalised match
        if norm in self._alias_index:
            return MappingResult(
                raw_name=raw_name,
                normalized_name=norm,
                mapped_field=self._alias_index[norm],
                confidence=0.9,
                strategy="normalized",
            )

        # 3. Keyword match — search in underscore-split tokens so that
        #    "qty" matches inside "total_qty" (normalised form of "total qty").
        norm_spaced = norm.replace("_", " ")
        for alias, canonical in self._alias_index.items():
            alias_spaced = alias.replace("_", " ")
            pattern = r"(?<![a-z0-9])" + re.escape(alias_spaced) + r"(?![a-z0-9])"
            if re.search(pattern, norm_spaced):
                return MappingResult(
                    raw_name=raw_name,
                    normalized_name=norm,
                    mapped_field=canonical,
                    confidence=0.6,
                    strategy="keyword",
                )

        return MappingResult(
            raw_name=raw_name,
            normalized_name=norm,
            mapped_field=None,
            confidence=0.0,
            strategy="none",
        )

    def _rebuild_index(self) -> None:
        self._alias_index = {}
        for canonical, aliases in self.mapping.items():
            for alias in aliases:
                self._alias_index[alias] = canonical
                self._alias_index[self._normalize(alias)] = canonical

    @staticmethod
    def _normalize(name: str) -> str:
        """Lowercase, strip, collapse whitespace/special chars to underscores."""
        name = name.lower().strip()
        name = re.sub(r"[\s\-./\\]+", "_", name)
        name = re.sub(r"[^a-z0-9_]", "", name)
        name = re.sub(r"_+", "_", name).strip("_")
        return name
