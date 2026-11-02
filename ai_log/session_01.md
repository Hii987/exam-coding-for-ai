# Séance 01 — 2026-11-02 — squelette du projet avec Claude Code

**Export de la conversation : À AJOUTER** (`ai_log/session_01_export.md`, exporté
depuis claude.ai/code).

## Ce que j'ai décidé

- Sujet : *analyste de données avec arbitre* (idée du sujet), briques 1, 3, 6, 8, 9.
- Modèle : Qwen3.5-4B via Ollama.
- Données : Citi Bike Jersey City, septembre 2024 (opendata.paris.fr et
  data.gouv.fr étaient bloqués dans l'environnement de l'IA ; le fichier S3 de
  Citi Bike était accessible et ne contient pas de données personnelles).

## Ce que l'IA a écrit, et ce qui a été corrigé

| fichier | statut | détail |
|---|---|---|
| `analyst/cleaning.py` | **corrigé** | 1re version : les 321 trajets vers des stations à id numérique étaient retirés (« préfixe inconnu »). En lisant les noms (« E 40 St & Park Ave ») on a vu que c'est Manhattan : la règle est devenue `city_of()` avec `New York`. |
| `analyst/guard.py` | **corrigé** | `test_score` a montré que « 0,739 » était lu 739 (pris pour un séparateur de milliers). Correction : un nombre avec séparateur de milliers ne commence pas par 0 (`[1-9]\d{0,2}` dans `NUM_RE` et `THOUSANDS_RE`). Test ajouté : `test_leading_zero_is_a_decimal_not_thousands`. |
| `analyst/guard.py` | **corrigé** | espaces insécables invisibles dans les regex remplacés par ` ` / ` `, pour pouvoir expliquer la ligne. |
| `tests/test_sandbox.py`, `tests/test_bench.py` | **corrigé** | moyenne attendue fausse dans le test : (10 + 20 + 40 + 5) / 4 = 18,75, pas 21,25. C'est le test qui était faux, pas le code. |
| `analyst/sandbox.py` | **corrigé** | ajout d'attributs interdits (`os`, `io`, `lib`, …) après avoir vu que `pd.io.common.os.system` passait par un attribut et non un nom. |
| `analyst/stats.py`, `agent.py`, `llm.py`, `bench/` | gardé tel quel | à relire ligne par ligne avant la soutenance. |
| `analyst/cleaning.py`, règle des 24 h | **à vérifier par moi** | la source citée (règles de location Citi Bike) doit être retrouvée mot pour mot. |

## Les trois questions (section 8 du sujet)

- *Est-ce que je sais ce que fait chaque ligne ?* — à faire : relire `guard.py`
  et `sandbox.py` en priorité (ce sont les plus probables à l'oral).
- *Cas limites ?* — couverts par des tests : série vide et une seule valeur
  (`test_single_value_and_empty`), proportion 0/n (`test_prop_ci_wilson_known`),
  réponse sans chiffre (`test_no_number_answer_passes`), code sans `result`.
- *Qu'est-ce que je lance pour vérifier ?* — `python -m pytest -q` (59 tests).
