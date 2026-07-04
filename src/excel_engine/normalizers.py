"""
Normalisation hooks for text, numbers, and units.

All functions are pure — they accept a value and return a normalised value.
They are intentionally kept as thin transformation hooks so that callers
can chain them, override them, or swap them out without altering the rest
of the pipeline.

Persian / Arabic character maps follow Unicode recommendations for Arabic
Presentation Forms and common substitutions used in Persian (Farsi) text.
"""

from __future__ import annotations

import re
import unicodedata

# ---------------------------------------------------------------------------
# Character maps
# ---------------------------------------------------------------------------

# Persian/Arabic character normalisation table.
# Maps Arabic-specific code points → their Persian (Farsi) equivalents,
# and normalises Arabic Presentation Forms → their base forms.
_ARABIC_TO_PERSIAN: dict[str, str] = {
    "\u0643": "\u06a9",  # ك (Arabic Kaf) → ک (Persian Kaf)
    "\u064a": "\u06cc",  # ي (Arabic Ya) → ی (Persian Ya)
    "\u0649": "\u06cc",  # ى (Alef Maqsura) → ی
    "\u0622": "\u0627",  # آ (Alef with Madda) → ا
    "\u0623": "\u0627",  # أ (Alef with Hamza above) → ا
    "\u0625": "\u0627",  # إ (Alef with Hamza below) → ا
    "\u0671": "\u0627",  # ٱ (Alef Wasla) → ا
    "\u06c0": "\u0647",  # ۀ (Heh with Ye above) → ه
    "\u06be": "\u0647",  # ﮬ (Heh Doachashmee) → ه
}

# Persian/Eastern Arabic numerals → ASCII digits
_PERSIAN_NUMERALS: dict[str, str] = {
    "\u06f0": "0",
    "\u06f1": "1",
    "\u06f2": "2",
    "\u06f3": "3",
    "\u06f4": "4",
    "\u06f5": "5",
    "\u06f6": "6",
    "\u06f7": "7",
    "\u06f8": "8",
    "\u06f9": "9",
    # Eastern Arabic numerals (used in Arabic)
    "\u0660": "0",
    "\u0661": "1",
    "\u0662": "2",
    "\u0663": "3",
    "\u0664": "4",
    "\u0665": "5",
    "\u0666": "6",
    "\u0667": "7",
    "\u0668": "8",
    "\u0669": "9",
}

# ---------------------------------------------------------------------------
# Text normalisation
# ---------------------------------------------------------------------------


def normalize_persian(text: str) -> str:
    """
    Normalise Persian (Farsi) text.

    - Replaces Arabic Kaf/Ya with their Persian equivalents.
    - Collapses Arabic Alef variants to plain Alef.
    - Removes Arabic diacritics (tashkeel).
    - Normalises Persian/Eastern-Arabic numerals to ASCII digits.
    - Strips leading/trailing whitespace.

    Args:
        text: Input string, possibly containing Arabic/Persian characters.

    Returns:
        Normalised string.
    """
    for arabic, persian in _ARABIC_TO_PERSIAN.items():
        text = text.replace(arabic, persian)
    # Remove diacritics (harakat / tashkeel): Unicode category Mn
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    for persian_digit, ascii_digit in _PERSIAN_NUMERALS.items():
        text = text.replace(persian_digit, ascii_digit)
    return text.strip()


def normalize_arabic(text: str) -> str:
    """
    Normalise Arabic text.

    - Collapses Alef variants to plain Alef.
    - Removes diacritics (tashkeel).
    - Normalises Eastern-Arabic numerals to ASCII digits.
    - Strips leading/trailing whitespace.

    Note: Unlike :func:`normalize_persian`, this function does *not* replace
    Arabic Kaf/Ya because those are valid in Arabic orthography.

    Args:
        text: Input string.

    Returns:
        Normalised string.
    """
    alef_variants = {"\u0622", "\u0623", "\u0625", "\u0671"}
    for variant in alef_variants:
        text = text.replace(variant, "\u0627")
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    for arabic_digit, ascii_digit in _PERSIAN_NUMERALS.items():
        text = text.replace(arabic_digit, ascii_digit)
    return text.strip()


def normalize_header(header: str) -> str:
    """
    Normalise a column header label into a snake_case identifier.

    - Lowercases.
    - Replaces spaces, hyphens, dots, and slashes with underscores.
    - Strips non-alphanumeric characters.
    - Collapses consecutive underscores.

    Args:
        header: Raw header string.

    Returns:
        Snake_case identifier string.
    """
    header = header.strip().lower()
    header = re.sub(r"[\s\-./\\]+", "_", header)
    header = re.sub(r"[^a-z0-9_\u0600-\u06ff]", "", header)  # keep Arabic/Persian chars
    header = re.sub(r"_+", "_", header).strip("_")
    return header


def normalize_whitespace(text: str) -> str:
    """Collapse consecutive whitespace into a single space and strip ends."""
    return re.sub(r"\s+", " ", text).strip()


# ---------------------------------------------------------------------------
# Numeric normalisation
# ---------------------------------------------------------------------------

_THOUSANDS_SEP = re.compile(r"[,،]")  # ASCII comma + Arabic comma
_DECIMAL_SEP = re.compile(r"\.")


def normalize_number(value: str) -> float | None:
    """
    Parse a human-entered numeric string into a Python float.

    Handles:
    - Persian/Eastern-Arabic numerals.
    - Thousands separators (, and ،).
    - European decimal notation (e.g., ``1.234,56``).

    Args:
        value: Raw string representation of a number.

    Returns:
        Parsed float, or *None* if the value cannot be interpreted.
    """
    # Normalise Persian/Arabic digits first
    for p, a in _PERSIAN_NUMERALS.items():
        value = value.replace(p, a)

    value = value.strip()

    # Detect European format: dots as thousands, comma as decimal
    # e.g., "1.234,56" → "1234.56"
    if re.search(r"\.\d{3},", value):
        value = value.replace(".", "").replace(",", ".")
    else:
        # Remove thousands separators (comma or Arabic comma)
        value = _THOUSANDS_SEP.sub("", value)

    try:
        return float(value)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Unit normalisation
# ---------------------------------------------------------------------------

# Default unit map: common abbreviations → canonical form.
# Callers may pass their own extended map to :func:`normalize_unit`.
DEFAULT_UNIT_MAP: dict[str, str] = {
    # Weight
    "kg": "kilogram",
    "kgs": "kilogram",
    "kilogram": "kilogram",
    "kilograms": "kilogram",
    "g": "gram",
    "gr": "gram",
    "gram": "gram",
    "grams": "gram",
    "lb": "pound",
    "lbs": "pound",
    "pound": "pound",
    "pounds": "pound",
    "t": "tonne",
    "ton": "tonne",
    "tonne": "tonne",
    "tonnes": "tonne",
    # Length
    "m": "meter",
    "meter": "meter",
    "meters": "meter",
    "metre": "meter",
    "metres": "meter",
    "cm": "centimeter",
    "centimeter": "centimeter",
    "mm": "millimeter",
    "millimeter": "millimeter",
    "km": "kilometer",
    "kilometer": "kilometer",
    "ft": "foot",
    "foot": "foot",
    "feet": "foot",
    "in": "inch",
    "inch": "inch",
    "inches": "inch",
    # Volume
    "l": "liter",
    "lt": "liter",
    "liter": "liter",
    "litre": "liter",
    "ml": "milliliter",
    "milliliter": "milliliter",
    # Count
    "pcs": "piece",
    "pc": "piece",
    "piece": "piece",
    "pieces": "piece",
    "ea": "each",
    "each": "each",
    "set": "set",
    "sets": "set",
    "box": "box",
    "boxes": "box",
    # Currency
    "usd": "USD",
    "$": "USD",
    "eur": "EUR",
    "€": "EUR",
    "gbp": "GBP",
    "£": "GBP",
    "rial": "IRR",
    "irr": "IRR",
    "تومان": "IRR",
    "ریال": "IRR",
}


def normalize_unit(unit: str, unit_map: dict[str, str] | None = None) -> str:
    """
    Map a raw unit string to its canonical form.

    Args:
        unit: Raw unit label (e.g., ``"Kg"``, ``"KGS"``, ``"تومان"``).
        unit_map: Optional custom map.  Falls back to :data:`DEFAULT_UNIT_MAP`.

    Returns:
        Canonical unit string, or the original (lowercased/stripped) value
        if no mapping is found.
    """
    effective_map = unit_map if unit_map is not None else DEFAULT_UNIT_MAP
    key = unit.strip().lower()
    return effective_map.get(key, effective_map.get(unit.strip(), key))
