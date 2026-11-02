# Données

Rien n'est stocké ici dans Git : `python scripts/prepare_data.py` télécharge
`JC-202409-citibike-tripdata.csv.zip` (Citi Bike, données ouvertes, sans donnée
personnelle) dans `data/raw/`, vérifie son SHA-256, écrit les données propres
dans `data/clean/` et le journal `cleaning_log.md` / `cleaning_log.json` ici.

Licence : Citi Bike Data License Agreement (https://ride.citibikenyc.com/data-sharing-policy).
