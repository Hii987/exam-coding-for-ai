"""Brique 3 : l'arbitre refuse tout chiffre qui n'a pas été calculé par le code."""
import pytest

from analyst.guard import check_answer, extract_numbers


@pytest.mark.parametrize("text,values", [
    ("115 308 trajets", [115308]),
    ("115,308 trips", [115308]),
    ("9,78 minutes", [9.78]),
    ("1 234,5 et 1,234.5", [1234.5, 1234.5]),
    ("73.89 %", [73.89]),
    ("le 2024-09-13 à 17h", [17]),
    ("aucun chiffre", []),
])
def test_extract_numbers(text, values):
    assert [v for _, v, _ in extract_numbers(text)] == values


def test_invented_number_is_blocked():
    v = check_answer("Il y a 120 000 trajets.", ["115308"])
    assert not v["ok"] and v["unsupported"] == ["120 000"]


def test_computed_number_passes_even_rounded_or_formatted():
    out = ["9.781234", "0.738908", "115308"]
    assert check_answer("Durée moyenne : 9,78 min.", out)["ok"]
    assert check_answer("73,9 % des trajets sont des abonnés.", out)["ok"]
    assert check_answer("115 308 trajets au total.", out)["ok"]


def test_wrong_rounding_is_blocked():
    assert not check_answer("Durée moyenne : 9,9 min.", ["9.781234"])["ok"]


def test_numbers_from_question_are_allowed():
    q = "Quels sont les 3 jours les plus chargés de 2024 ?"
    assert check_answer("Voici les 3 jours de 2024 : ...", [], question=q)["ok"]


def test_dates_must_be_in_evidence():
    assert check_answer("Le jour le plus chargé est le 2024-09-13.", ["2024-09-13    5210"])["ok"]
    v = check_answer("Le jour le plus chargé est le 2024-09-21.", ["2024-09-13    5210"])
    assert not v["ok"] and "2024-09-21" in v["unsupported"]


def test_no_number_answer_passes():
    assert check_answer("La station la plus fréquente est Grove St.", [])["ok"]


def test_leading_zero_is_a_decimal_not_thousands():
    assert [v for _, v, _ in extract_numbers("soit 0,739")] == [0.739]
