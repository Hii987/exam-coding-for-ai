"""Douze tâches à réponse connue (brique 9).

La réponse attendue est calculée par du code pandas écrit à la main (pas par le
modèle) sur les données nettoyées, puis figée dans bench/expected.json.
"""
from __future__ import annotations

import pandas as pd


def _mode_station(df):
    return df["start_station_name"].value_counts().idxmax()


TASKS = [
    {"id": "t01", "question": "Combien de trajets y a-t-il dans les données ?",
     "ref": lambda d: len(d), "kind": "number", "tol": 0.0},
    {"id": "t02", "question": "Quel pourcentage des trajets a été fait par des abonnés (member) ?",
     "ref": lambda d: 100 * (d["member_casual"] == "member").mean(), "kind": "number", "tol": 0.01},
    {"id": "t03", "question": "Quelle est la durée moyenne d'un trajet, en minutes ?",
     "ref": lambda d: d["duration_min"].mean(), "kind": "number", "tol": 0.01},
    {"id": "t04", "question": "Quelle est la durée médiane, en minutes, des trajets en vélo électrique ?",
     "ref": lambda d: d.loc[d["rideable_type"] == "electric_bike", "duration_min"].median(),
     "kind": "number", "tol": 0.01},
    {"id": "t05", "question": "Quelle est la station de départ la plus fréquente ?",
     "ref": _mode_station, "kind": "text"},
    {"id": "t06", "question": "Combien de stations de départ différentes y a-t-il ?",
     "ref": lambda d: d["start_station_name"].nunique(), "kind": "number", "tol": 0.0},
    {"id": "t07", "question": "Combien de trajets ont commencé à Hoboken ?",
     "ref": lambda d: int((d["start_city"] == "Hoboken").sum()), "kind": "number", "tol": 0.0},
    {"id": "t08", "question": "Quel jour (date AAAA-MM-JJ) a compté le plus de trajets ?",
     "ref": lambda d: str(d["started_at"].dt.date.value_counts().idxmax()), "kind": "text"},
    {"id": "t09", "question": "De combien de minutes la durée moyenne des trajets des "
                              "occasionnels (casual) dépasse-t-elle celle des abonnés (member) ?",
     "ref": lambda d: d.loc[d["member_casual"] == "casual", "duration_min"].mean()
                      - d.loc[d["member_casual"] == "member", "duration_min"].mean(),
     "kind": "number", "tol": 0.01},
    {"id": "t10", "question": "Parmi les trajets des occasionnels (casual), quel pourcentage "
                              "a été fait en vélo électrique ?",
     "ref": lambda d: 100 * (d.loc[d["member_casual"] == "casual", "rideable_type"]
                             == "electric_bike").mean(), "kind": "number", "tol": 0.01},
    {"id": "t11", "question": "À quelle heure de la journée (0 à 23) part le plus grand nombre de trajets ?",
     "ref": lambda d: int(d["started_at"].dt.hour.value_counts().idxmax()), "kind": "number",
     "tol": 0.0},
    {"id": "t12", "question": "Combien de trajets se terminent à New York ?",
     "ref": lambda d: int((d["end_city"] == "New York").sum()), "kind": "number", "tol": 0.0},
]


def compute_expected(df: pd.DataFrame) -> dict:
    out = {}
    for t in TASKS:
        v = t["ref"](df)
        out[t["id"]] = round(float(v), 4) if t["kind"] == "number" else str(v)
    return out
