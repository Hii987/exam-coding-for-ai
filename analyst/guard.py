"""L'arbitre (brique 3) : aucun chiffre dans la réponse finale s'il n'a pas été
calculé par du code.

Règle imposée par le code : chaque nombre et chaque date de la réponse doit se
retrouver dans les sorties des outils de la session (ou dans la question).
Sinon la réponse est refusée, quoi que dise le prompt.
"""
from __future__ import annotations

import re

DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2}(?::\d{2})?)?\b")
# 1 234,5 / 1,234.5 / 1234.5 / 12,5 / -3 / 45 %
NUM_RE = re.compile(
    r"(?<![\w.])[-−]?(?:[1-9]\d{0,2}(?:[ \u00a0\u202f,]\d{3})+(?![\d])(?:[.,]\d+)?|\d+(?:[.,]\d+)?)"
)
THOUSANDS_RE = re.compile(r"^(-?[1-9]\d{0,2}(?:[ ,]\d{3})+)(?:[.,](\d+))?$")


def _to_float(tok: str) -> tuple[float, int]:
    """Texte -> (valeur, nombre de décimales affichées)."""
    t = tok.replace("−", "-").replace("\u00a0", " ").replace("\u202f", " ")
    m = THOUSANDS_RE.match(t)
    if m:
        # "115 558", "115,558", "1 234,5", "1,234.5" : groupes de 3 = milliers
        # (choix assumé : "12,500" est lu 12500, pas 12,5)
        t = re.sub(r"[ ,]", "", m.group(1)) + ("." + m.group(2) if m.group(2) else "")
    else:
        t = t.replace(" ", "").replace(",", ".")  # virgule décimale française
    dec = len(t.split(".")[1]) if "." in t else 0
    return float(t), dec


def extract_numbers(text: str) -> list[tuple[str, float, int]]:
    """Liste de (texte, valeur, décimales). Les dates sont retirées avant."""
    text = DATE_RE.sub(" ", text)
    found = []
    for m in NUM_RE.finditer(text):
        tok = m.group(0).strip()
        try:
            v, d = _to_float(tok)
        except ValueError:
            continue
        found.append((tok, v, d))
    return found


def extract_dates(text: str) -> list[str]:
    return [m.group(0)[:10] for m in DATE_RE.finditer(text)]


def evidence_values(texts: list[str]) -> set[float]:
    vals: set[float] = set()
    for t in texts:
        for _, v, _ in extract_numbers(t):
            vals.add(v)
            vals.add(v * 100)  # une proportion 0.738 peut s'écrire 73,8 %
            vals.add(v / 60)   # secondes -> minutes
            vals.add(v * 60)   # minutes -> secondes
    return vals


def matches(value: float, decimals: int, evidence: set[float], rel_tol: float = 0.005) -> bool:
    for e in evidence:
        if round(e, decimals) == round(value, decimals):
            return True
        if round(abs(e), decimals) == round(abs(value), decimals):
            return True  # "3,2 min de moins" pour une différence de -3,2
        if e != 0 and abs(value - e) <= rel_tol * abs(e):
            return True
    return False


def check_answer(answer: str, tool_outputs: list[str], question: str = "") -> dict:
    """Renvoie {"ok": bool, "unsupported": [...]} : les chiffres non justifiés."""
    evidence = evidence_values(tool_outputs + [question])
    unsupported = []
    for tok, v, d in extract_numbers(answer):
        if not matches(v, d, evidence):
            unsupported.append(tok)
    evidence_text = "\n".join(tool_outputs + [question])
    for date in extract_dates(answer):
        if date not in evidence_text:
            unsupported.append(date)
    return {"ok": not unsupported, "unsupported": unsupported}
