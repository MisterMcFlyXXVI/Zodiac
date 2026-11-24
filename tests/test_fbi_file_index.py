"""Page tagging for the FBI-file index. Uses only short synthetic snippets, never real OCR text."""
import importlib.util
import os

_spec = importlib.util.spec_from_file_location(
    "fbi_file_index", os.path.join(os.path.dirname(__file__), "..", "scripts", "fbi_file_index.py"))
fbi = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fbi)


def tags(text, part="F1", page=1):
    return set(fbi.tag_page(text, part, page))


def test_keyword_tags():
    assert tags("no decryption could be effected for the cipher") == {"crypt"}
    assert tags("A photocopy of the letter with 13 characters") == {"photo", "c13"}
    assert "c32" in tags("a 32-character cryptogram")
    assert "c340" in tags("the 340 cipher") and "c408" in tags("the 408 cipher")
    assert "item" in tags("Specimens received: Qc46 and Kc3")
    assert "hw" in tags("handwriting comparison")


def test_no_false_tags_on_plain_text():
    assert fbi.tag_page("memo regarding a vehicle seen on Tuesday", "F1", 1) == []
    assert fbi.tag_page("", "F1", 1) == []
    assert "c408" not in tags("room 4080 and 1408")  # \b408\b needs a word boundary
    assert "item" not in tags("Q1234 and Qc1234")  # item numbers have at most 3 digits


def test_matching_is_case_insensitive():
    assert tags("CIPHER") == {"crypt"} and tags("My Name Is") == {"c13"}


def test_manual_tags_apply_only_to_their_page_and_part():
    assert "z13_letter_image" in tags("", "P09", 210)
    assert "z32_letter_image" in tags("", "P09", 215)
    assert "z13_letter_image" not in tags("", "P09", 215)
    assert "z13_letter_image" not in tags("", "P10", 210)
    assert "evidence_image" in tags("", "P09", 168) and "evidence_image" in tags("", "P09", 262)
    assert "evidence_image" not in tags("", "P09", 167) and "evidence_image" not in tags("", "P09", 263)
    assert "lab_cryptanalysis_request" in tags("", "F3", 169)
    assert "lab_cryptanalysis_request" not in tags("", "F3", 174)


def test_manual_tag_is_not_duplicated_when_keyword_also_matches():
    t = fbi.tag_page("cipher", "P09", 215)
    assert len(t) == len(set(t)) and "crypt" in t and "symbols_image" in t


def test_cipher_page_definition():
    assert fbi.is_cipher_page(["crypt"])
    assert fbi.is_cipher_page(["photo", "z13_letter_image"])
    assert not fbi.is_cipher_page(["photo", "item", "hw", "evidence_image"])
    assert not fbi.is_cipher_page([])


def test_every_manual_tag_names_a_known_part_and_valid_range():
    for tag, part, a, b in fbi.MANUAL:
        assert part in fbi.PDFS and 1 <= a <= b, (tag, part, a, b)
