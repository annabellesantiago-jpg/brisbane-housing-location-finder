"""Normalise source column names to snake_case for Bronze tables (decision B5).

Only column names change; values are never modified. Names that start with an
underscore are reserved for the audit columns added by Bronze (decision B6), so
normalised source names never start with one.

Names are reduced to ASCII letters, digits and underscores, because Databricks
SQL only accepts those in unquoted identifiers. Latin letters are transliterated
rather than dropped ("Café" -> "cafe", "Straße" -> "strasse", "Øre" -> "ore").

Transliteration scope: every letter in the Unicode Latin-1 Supplement, Latin
Extended-A, Latin Extended-B and Latin Extended Additional blocks
(U+00C0-U+024F, U+1E00-U+1EFF) maps to ASCII letters, except the few listed in
``LATIN_LETTERS_WITHOUT_ASCII_EQUIVALENT`` (tone letters, click letters and
glottal stops). Those, and letters from other scripts (e.g. Chinese, Cyrillic),
are treated as separators. A name with no ASCII letters or digits left gets a
positional fallback name instead of failing the load; the original name is kept
in the mapping so it can be recorded in the data dictionary.
"""

import logging
import re
import unicodedata
from collections.abc import Iterable

logger = logging.getLogger(__name__)

_NON_ASCII_ALPHANUMERIC = re.compile(r"[^0-9A-Za-z]+")

# Latin letters that have no Unicode decomposition, so NFKD cannot reduce them
# to an ASCII base letter. Keys are lower case because names are casefolded
# first (e.g. "Ø" -> "ø", "Ɓ" -> "ɓ"). Values are the usual ASCII spelling.
_LATIN_FOLDS: dict[str, str] = {
    "\u00b7": "",  # middle dot, left over from "ŀ" in Catalan "l·l": removed
    "æ": "ae", "ð": "d", "ø": "o", "þ": "th", "đ": "d", "ħ": "h", "ı": "i",
    "ĸ": "k", "ł": "l", "ŋ": "ng", "œ": "oe", "ŧ": "t",
    "ƀ": "b", "ƃ": "b", "ƈ": "c", "ƌ": "d", "ƍ": "d", "ƒ": "f", "ƕ": "hv",
    "ƙ": "k", "ƚ": "l", "ƛ": "l", "ƞ": "n", "ƣ": "oi", "ƥ": "p", "ƫ": "t",
    "ƭ": "t", "ƴ": "y", "ƶ": "z", "ƹ": "z", "ƺ": "z", "ƿ": "w", "ǝ": "e",
    "ǥ": "g", "ȝ": "y", "ȡ": "d", "ȣ": "ou", "ȥ": "z", "ȴ": "l", "ȵ": "n",
    "ȶ": "t", "ȷ": "j", "ȸ": "db", "ȹ": "qp", "ȼ": "c", "ȿ": "s", "ɀ": "z",
    "ɇ": "e", "ɉ": "j", "ɋ": "q", "ɍ": "r", "ɏ": "y",
    "ɓ": "b", "ɔ": "o", "ɖ": "d", "ɗ": "d", "ə": "e", "ɛ": "e", "ɠ": "g",
    "ɣ": "g", "ɨ": "i", "ɩ": "i", "ɯ": "m", "ɲ": "n", "ɵ": "o", "ʀ": "r",
    "ʃ": "sh", "ʈ": "t", "ʉ": "u", "ʊ": "u", "ʋ": "v", "ʌ": "v", "ʒ": "z",
    "ẜ": "s", "ẝ": "s", "ẟ": "d", "ỻ": "ll", "ỽ": "v", "ỿ": "y",
    "ⱥ": "a", "ⱦ": "t",
}  # fmt: skip
_LATIN_FOLD_TABLE = str.maketrans(_LATIN_FOLDS)

# Latin letters in the blocks above that stand for a tone, a click or a glottal
# stop and have no ASCII letter equivalent. They are treated as separators.
LATIN_LETTERS_WITHOUT_ASCII_EQUIVALENT = frozenset("ƄƅƧƨƼƽǀǁǂǃɁɂƾƻƪ")


def _to_ascii(name: str) -> str:
    """Transliterate the Latin letters in a name to ASCII.

    ``casefold`` turns "ß" into "ss"; NFKD then splits accented letters into
    base letter + accent ("é" -> "e" + "´") and full-width or ligature forms into
    plain letters ("Ｗ" -> "W", "ﬁ" -> "fi"); the accents are then removed.
    Latin letters with no decomposition ("ø", "æ", "ł", ...) are replaced from
    ``_LATIN_FOLDS``. Anything else that is not ASCII (e.g. Chinese, Cyrillic)
    is left as it is and treated as a separator by the caller.
    """
    decomposed = unicodedata.normalize("NFKD", name.casefold())
    without_accents = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return without_accents.translate(_LATIN_FOLD_TABLE)


def to_snake_case(name: str) -> str:
    """Convert one source column name to an ASCII snake_case name.

    After transliteration to ASCII, every run of characters that is not an
    ASCII letter or digit becomes a single underscore; leading and trailing
    underscores are removed. A name that would start with a digit gets the
    prefix ``c_``.

    Examples:
        "Centre Code" -> "centre_code"
        "SUBURB_NAME" -> "suburb_name"
        "addr:street" -> "addr_street"
        "Café"        -> "cafe"
        "Øre"         -> "ore"
        "@id"         -> "id"

    Args:
        name: Column name as it appears in the source file.

    Returns:
        The snake_case name.

    Raises:
        ValueError: If nothing usable remains, e.g. "", "@@" or "名前".
    """
    snake = _NON_ASCII_ALPHANUMERIC.sub("_", _to_ascii(name)).strip("_")
    if not snake:
        raise ValueError(f"Column name {name!r} has no ASCII letters or digits")
    if snake[0].isdigit():
        snake = f"c_{snake}"
    return snake


def build_column_mapping(columns: Iterable[str]) -> dict[str, str]:
    """Map each source column name to its snake_case name.

    A column whose name has no ASCII letters or digits is named ``c_<position>``
    (1-based position in the file) and a warning is logged, so one such column
    does not stop the whole dataset from loading.

    Args:
        columns: Source column names, in file order.

    Returns:
        A dict from original name to snake_case name, in the same order.

    Raises:
        ValueError: If two source columns would get the same name, e.g.
            "Centre Code" and "centre_code", or "Résumé" and "resume".
    """
    mapping: dict[str, str] = {}
    seen: dict[str, str] = {}
    for position, original in enumerate(columns, start=1):
        try:
            new = to_snake_case(original)
        except ValueError:
            new = f"c_{position}"
            logger.warning(
                "Column %r has no ASCII letters or digits; named %r", original, new
            )
        if new in seen:
            raise ValueError(
                f"Columns {seen[new]!r} and {original!r} both normalise to {new!r}"
            )
        seen[new] = original
        mapping[original] = new
    return mapping
