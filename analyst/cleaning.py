"""Nettoyage des trajets Citi Bike, avec un journal de chaque décision (brique 6).

Chaque étape écrit dans le journal : combien de lignes avant/après, pourquoi,
et d'où vient la règle (le fichier, un document, ou notre propre décision).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

# Règles qui ne sont PAS dans le fichier CSV : elles viennent de documents.
RULES = {
    "min_60s": {
        "rule": "Les trajets de moins de 60 secondes ne sont pas de vrais trajets "
                "(faux départs, re-dépôt du vélo) ; les trajets du personnel et des "
                "stations de test non plus.",
        "source": "Citi Bike, page 'System Data' (https://citibikenyc.com/system-data)",
    },
    "max_24h": {
        "rule": "Un vélo non rendu au bout de 24 heures est considéré comme perdu ou "
                "volé : un 'trajet' de plus de 24 h n'est pas un trajet.",
        "source": "Citi Bike, contrat de location / FAQ tarifs "
                  "(https://citibikenyc.com/pricing) - à vérifier et citer précisément",
    },
    "city_prefix": {
        "rule": "Le préfixe de l'identifiant de station donne la ville : "
                "HB = Hoboken, JC = Jersey City ; un identifiant numérique (ex. 6432.11) "
                "est une station de New York.",
        "source": "Carte des stations Citi Bike (stations HBxxx toutes à Hoboken) ; "
                  "vérifié sur les coordonnées : les ids numériques sont à Manhattan "
                  "(longitude > -74.02, ex. 'E 40 St & Park Ave')",
    },
}

CITY_PREFIX = {"HB": "Hoboken", "JC": "Jersey City"}
NYC_ID = re.compile(r"^\d{4}\.\d{2}$")


def city_of(station_id) -> str | None:
    s = str(station_id)
    if s[:2] in CITY_PREFIX:
        return CITY_PREFIX[s[:2]]
    if NYC_ID.match(s):
        return "New York"
    return None


class CleaningLog:
    def __init__(self) -> None:
        self.steps: list[dict] = []

    def add(self, step: str, before: int, after: int, reason: str,
            source: str = "décision de l'analyste", changed: int | None = None) -> None:
        self.steps.append({
            "step": step,
            "rows_before": int(before),
            "rows_after": int(after),
            "rows_removed": int(before - after),
            "values_changed": None if changed is None else int(changed),
            "reason": reason,
            "source": source,
        })

    def to_markdown(self) -> str:
        lines = ["| étape | avant | après | retirées | valeurs modifiées | raison | source |",
                 "|---|---|---|---|---|---|---|"]
        for s in self.steps:
            ch = "" if s["values_changed"] is None else s["values_changed"]
            lines.append(f"| {s['step']} | {s['rows_before']} | {s['rows_after']} | "
                         f"{s['rows_removed']} | {ch} | {s['reason']} | {s['source']} |")
        return "\n".join(lines)


def clean(raw: pd.DataFrame) -> tuple[pd.DataFrame, CleaningLog]:
    """Renvoie (données propres, journal). Ne modifie pas `raw`."""
    log = CleaningLog()
    df = raw.copy()
    n = len(df)

    # 1. Doublons d'identifiant de trajet
    df = df.drop_duplicates(subset="ride_id")
    log.add("doublons ride_id", n, len(df), "un trajet = une ligne")
    n = len(df)

    # 2. Dates : texte -> datetime ; lignes illisibles retirées
    df["started_at"] = pd.to_datetime(df["started_at"], errors="coerce", format="mixed")
    df["ended_at"] = pd.to_datetime(df["ended_at"], errors="coerce", format="mixed")
    df = df.dropna(subset=["started_at", "ended_at"])
    log.add("dates illisibles", n, len(df),
            "started_at/ended_at convertis en datetime ; lignes non convertibles retirées",
            changed=2 * len(df))
    n = len(df)

    df["duration_min"] = (df["ended_at"] - df["started_at"]).dt.total_seconds() / 60

    # 3. Durée négative ou nulle : impossible
    df = df[df["duration_min"] > 0]
    log.add("durée <= 0", n, len(df), "fin avant le début : erreur d'horodatage")
    n = len(df)

    # 4. Règle du document : < 60 s
    df = df[df["duration_min"] >= 1]
    log.add("durée < 60 s", n, len(df), RULES["min_60s"]["rule"], RULES["min_60s"]["source"])
    n = len(df)

    # 5. Règle du document : > 24 h
    df = df[df["duration_min"] <= 24 * 60]
    log.add("durée > 24 h", n, len(df), RULES["max_24h"]["rule"], RULES["max_24h"]["source"])
    n = len(df)

    # 6. Libellés : id de station d'arrivée manquant alors que le nom est connu
    name_to_id = (pd.concat([
        df[["start_station_name", "start_station_id"]].set_axis(["name", "id"], axis=1),
        df[["end_station_name", "end_station_id"]].set_axis(["name", "id"], axis=1),
    ]).dropna().drop_duplicates("name").set_index("name")["id"])
    fixable = df["end_station_id"].isna() & df["end_station_name"].notna()
    df.loc[fixable, "end_station_id"] = df.loc[fixable, "end_station_name"].map(name_to_id)
    fixed = int((fixable & df["end_station_id"].notna()).sum())
    log.add("id station d'arrivée reconstitué", n, len(df),
            "id manquant mais nom présent : id retrouvé grâce au nom (même nom = même station)",
            changed=fixed)

    # 7. Pas de station d'arrivée : vélo non redéposé en station, trajet incomplet
    df = df[df["end_station_name"].notna() & df["end_station_id"].notna()]
    log.add("station d'arrivée manquante", n, len(df),
            "vélo non rendu en station (coordonnées arrondies à 0,01°) : trajet incomplet")
    n = len(df)

    # 8. Libellés normalisés
    for col in ["rideable_type", "member_casual"]:
        df[col] = df[col].astype(str).str.strip().str.lower()
    df["start_city"] = df["start_station_id"].map(city_of)
    df["end_city"] = df["end_station_id"].map(city_of)
    unknown = df["start_city"].isna() | df["end_city"].isna()
    df = df[~unknown]
    log.add("ville déduite de l'id de station", n, len(df),
            RULES["city_prefix"]["rule"] + " Id d'une autre forme : ligne retirée.",
            RULES["city_prefix"]["source"], changed=2 * len(df))
    n = len(df)

    df["round_trip"] = df["start_station_id"] == df["end_station_id"]
    df = df.reset_index(drop=True)
    return df, log


def load_clean(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, parse_dates=["started_at", "ended_at"])


def write_log(log: CleaningLog, json_path: Path) -> None:
    json_path.write_text(json.dumps({"rules": RULES, "steps": log.steps},
                                    ensure_ascii=False, indent=2), encoding="utf-8")
    json_path.with_suffix(".md").write_text(
        "# Journal de nettoyage\n\n" + log.to_markdown() + "\n", encoding="utf-8")
