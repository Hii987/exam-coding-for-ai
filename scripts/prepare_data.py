"""Télécharge les trajets Citi Bike (Jersey City, sept. 2024), les nettoie et
écrit le journal de nettoyage. Usage : python scripts/prepare_data.py"""
import hashlib
import io
import sys
import zipfile
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from analyst import config  # noqa: E402
from analyst.cleaning import clean, write_log  # noqa: E402

EXPECTED_SHA256 = "491ac433ec02bfa8e9c456075532b3b44aaa02f3b8503bb59e2b3bdd99db2a81"


def download() -> None:
    if config.RAW_CSV.exists():
        print(f"déjà téléchargé : {config.RAW_CSV}")
        return
    print(f"téléchargement de {config.DATA_URL}")
    r = requests.get(config.DATA_URL, timeout=300)
    r.raise_for_status()
    config.RAW_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        name = next(n for n in z.namelist() if n.endswith(".csv") and "MACOSX" not in n)
        config.RAW_CSV.write_bytes(z.read(name))


def main() -> None:
    download()
    sha = hashlib.sha256(config.RAW_CSV.read_bytes()).hexdigest()
    print(f"sha256 du fichier brut : {sha}")
    if sha != EXPECTED_SHA256:
        print("ATTENTION : le fichier brut diffère de celui utilisé pour le benchmark")
    raw = pd.read_csv(config.RAW_CSV)
    df, log = clean(raw)
    config.CLEAN_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(config.CLEAN_CSV, index=False)
    write_log(log, config.CLEANING_LOG)
    print(log.to_markdown())
    print(f"\n{len(raw)} lignes brutes -> {len(df)} lignes propres : {config.CLEAN_CSV}")


if __name__ == "__main__":
    main()
