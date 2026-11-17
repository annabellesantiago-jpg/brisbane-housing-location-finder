import logging

import pytest

from brisbane_house_finder.bronze.column_names import (
    LATIN_LETTERS_WITHOUT_ASCII_EQUIVALENT,
    build_column_mapping,
    to_snake_case,
)

# Latin-1 Supplement, Latin Extended-A, Latin Extended-B, Latin Extended Additional
LATIN_BLOCKS = [*range(0x00C0, 0x0250), *range(0x1E00, 0x1F00)]
LATIN_LETTERS = [chr(cp) for cp in LATIN_BLOCKS if chr(cp).isalpha()]


@pytest.mark.parametrize(
    ("source_name", "expected"),
    [
        ("Centre Code", "centre_code"),  # schools CSV: spaces
        ("Statistical Area Level2", "statistical_area_level2"),
        ("Non-State Sector", "non_state_sector"),  # hyphen
        ("SUBURB_NAME", "suburb_name"),  # council GeoJSON: upper case
        ("OBJECTID", "objectid"),
        ("geo_point_2d", "geo_point_2d"),  # health GeoParquet: already snake_case
        ("addr:street", "addr_street"),  # OSM: colon
        ("not:brand:wikidata", "not_brand_wikidata"),
        ("phone:AU", "phone_au"),
        ("walk-in", "walk_in"),
        ("@id", "id"),  # OSM export: leading @
        ("  Latitude ", "latitude"),  # stray spaces
        ("_id", "id"),  # leading underscore is reserved for audit columns
        ("2022 Count", "c_2022_count"),  # cannot start with a digit
    ],
)
def test_to_snake_case(source_name, expected):
    assert to_snake_case(source_name) == expected


@pytest.mark.parametrize(
    ("source_name", "expected"),
    [
        ("Café", "cafe"),  # accent removed, letter kept
        ("Résumé Date", "resume_date"),
        ("Ñandú", "nandu"),
        ("Straße", "strasse"),  # sharp s has no accent to remove: casefold gives "ss"
        ("ＷＩＤＥ Name", "wide_name"),  # full-width letters
        ("ﬁle", "file"),  # ligature
        ("Café", "cafe"),  # same name written with a separate accent character
        ("名前 id", "id"),  # non-Latin part has no ASCII equivalent
        # Latin letters with no Unicode decomposition (need the explicit fold table)
        ("Øre", "ore"),
        ("Smørrebrød", "smorrebrod"),
        ("Æble", "aeble"),
        ("Œuvre", "oeuvre"),
        ("Łódź", "lodz"),
        ("Đường", "duong"),
        ("Þing", "thing"),
        ("Ħal", "hal"),
        ("Iıi", "iii"),  # dotless i
        ("İstanbul", "istanbul"),  # dotted capital I
        ("Paral·lel", "parallel"),  # Catalan middle dot
        ("Ŀlei", "llei"),
        ("Ɓauchi", "bauchi"),
        ("Ŋoma", "ngoma"),
    ],
)
def test_to_snake_case_transliterates_unicode(source_name, expected):
    assert to_snake_case(source_name) == expected


@pytest.mark.parametrize("bad_name", ["", "   ", "@@", "::", "名前", "Город"])
def test_to_snake_case_rejects_names_without_ascii_letters_or_digits(bad_name):
    with pytest.raises(ValueError):
        to_snake_case(bad_name)


def test_build_column_mapping_keeps_order():
    mapping = build_column_mapping(["Centre Code", "Centre Name", "Longitude"])
    assert list(mapping.items()) == [
        ("Centre Code", "centre_code"),
        ("Centre Name", "centre_name"),
        ("Longitude", "longitude"),
    ]


def test_build_column_mapping_rejects_collisions():
    with pytest.raises(ValueError, match="centre_code"):
        build_column_mapping(["Centre Code", "centre_code"])


def test_build_column_mapping_rejects_collisions_after_transliteration():
    with pytest.raises(ValueError, match="resume"):
        build_column_mapping(["Résumé", "resume"])


def test_build_column_mapping_uses_positional_fallback(caplog):
    with caplog.at_level(logging.WARNING):
        mapping = build_column_mapping(["Suburb", "名前", "Город"])
    assert mapping == {"Suburb": "suburb", "名前": "c_2", "Город": "c_3"}
    assert "名前" in caplog.text


def test_normalised_names_never_start_with_underscore():
    mapping = build_column_mapping(["_rescued", "__x", "@geometry"])
    assert not any(name.startswith("_") for name in mapping.values())


def test_normalised_names_are_valid_unquoted_sql_identifiers():
    names = ["Café", "Straße", "名前", "addr:street", "2022 Count", "ＷＩＤＥ"]
    for new in build_column_mapping(names).values():
        assert new.isascii()
        assert all(ch.isalnum() or ch == "_" for ch in new)
        assert not new[0].isdigit()


@pytest.mark.parametrize(
    "letter",
    [ch for ch in LATIN_LETTERS if ch not in LATIN_LETTERS_WITHOUT_ASCII_EQUIVALENT],
)
def test_every_latin_letter_in_scope_transliterates_to_ascii_letters(letter):
    result = to_snake_case(letter)
    assert result.isascii() and result.isalpha(), (letter, result)


@pytest.mark.parametrize("letter", sorted(LATIN_LETTERS_WITHOUT_ASCII_EQUIVALENT))
def test_latin_letters_without_ascii_equivalent_are_separators(letter):
    assert to_snake_case(f"a{letter}b") == "a_b"
