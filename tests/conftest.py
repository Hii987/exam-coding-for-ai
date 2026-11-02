import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def make_raw() -> pd.DataFrame:
    """Petit jeu brut au format Citi Bike, avec un défaut de chaque sorte."""
    rows = [
        # id, type, début, fin, station dép (nom, id), station arr (nom, id), membre
        ("A", "electric_bike", "2024-09-01 08:00:00.000", "2024-09-01 08:10:00.000", "Grove St", "JC005", "River St", "HB101", "member"),
        ("A", "electric_bike", "2024-09-01 08:00:00.000", "2024-09-01 08:10:00.000", "Grove St", "JC005", "River St", "HB101", "member"),  # doublon
        ("B", "classic_bike", "2024-09-01 09:00:00.000", "2024-09-01 09:00:30.000", "Grove St", "JC005", "Grove St", "JC005", "casual"),  # < 60 s
        ("C", "classic_bike", "2024-09-01 09:00:00.000", "2024-09-03 09:00:00.000", "Grove St", "JC005", "River St", "HB101", "casual"),  # > 24 h
        ("D", "Classic_Bike ", "2024-09-02 10:00:00.000", "2024-09-02 10:20:00.000", "River St", "HB101", "Grove St", None, "Casual"),  # id manquant, libellés sales
        ("E", "electric_bike", "2024-09-02 11:00:00.000", "2024-09-02 11:30:00.000", "River St", "HB101", None, None, "member"),  # pas d'arrivée
        ("F", "electric_bike", "2024-09-02 12:00:00.000", "2024-09-02 12:40:00.000", "Grove St", "JC005", "W 44 St & 5 Ave", "6551.02", "casual"),  # vers New York
        ("G", "electric_bike", "pas une date", "2024-09-02 12:40:00.000", "Grove St", "JC005", "River St", "HB101", "member"),  # date illisible
        ("H", "classic_bike", "2024-09-02 13:00:00.000", "2024-09-02 12:00:00.000", "Grove St", "JC005", "River St", "HB101", "member"),  # fin avant début
        ("I", "classic_bike", "2024-09-02 14:00:00.000", "2024-09-02 14:05:00.000", "Grove St", "JC005", "Grove St", "JC005", "member"),  # aller-retour
    ]
    cols = ["ride_id", "rideable_type", "started_at", "ended_at", "start_station_name",
            "start_station_id", "end_station_name", "end_station_id", "member_casual"]
    return pd.DataFrame(rows, columns=cols)


@pytest.fixture
def raw():
    return make_raw()


@pytest.fixture
def clean_df():
    from analyst.cleaning import clean
    return clean(make_raw())[0]
