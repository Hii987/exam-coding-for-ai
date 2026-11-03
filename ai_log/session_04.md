# Séance 04 — 2026-11-03 — benchmark v2 et échec de t08

**Export de la conversation : À AJOUTER** (même conversation que les séances précédentes).

## Résultats

Benchmark v2 (après la correction de la séance 03) : système 91,7 % (3 × 92 %),
modèle seul 8,3 %, 1 refus de l'arbitre, 1 691 tokens par tâche (contre 4 422 en v1).
Seule tâche ratée : t08 (jour le plus chargé), 0 sur 3.

## Ce que la trace de t08 a appris, et ce qui a été corrigé

| fichier | statut | détail |
|---|---|---|
| hypothèse de l'IA | **fausse** | l'IA pensait à un problème de format de date dans la réponse de Qwen (« 13 septembre »). La trace montre trois causes différentes. |
| `analyst/sandbox.py` | **corrigé** | dates renvoyées en texte ISO au lieu de `datetime.date(2024, 9, 13)` (fausse alerte de l'arbitre, lancement 2). |
| `analyst/sandbox.py` | **corrigé** | `__import__` interne sur liste blanche : `strftime` plantait avec `KeyError: '__import__'` (lancement 1). |
| `analyst/sandbox.py` | **renforcé** | en ajoutant `__import__`, un détour devenait possible (`__builtins__.get('_' + '_import__')`). Tout nom qui commence par « _ » est maintenant bloqué ; l'attaque est dans les tests. |
| erreur du modèle | **gardée** | grouper par horodatage exact au lieu du jour (lancements 1 et 3) : limite réelle de l'arbitre, qui vérifie l'origine d'un chiffre et pas la justesse du calcul. |
| `bench/run_bench.py` | ajouté | option `--out` pour relancer une tâche sans écraser les résultats ; `show_failures.py --dir`. |
