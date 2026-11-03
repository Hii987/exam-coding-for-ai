# Séance 03 — 2026-11-03 — benchmark réel et premier échec expliqué

**Export de la conversation : À AJOUTER** (même conversation que les séances 01 et 02).

## Ce que j'ai fait

- Lancé le benchmark sur mon Mac (Qwen3.5-4B, 3 lancements × 2 modes × 12 tâches).
  Système 52,8 % ± 19,2 ; modèle seul 11,1 % ± 4,8 ; 10 refus de l'arbitre.
- Lu les échecs avec `bench/show_failures.py --tasks t01,t12`.

## Ce que la trace a appris, et ce qui a été corrigé

| fichier | statut | détail |
|---|---|---|
| hypothèse de l'IA | **fausse** | l'IA pensait que Qwen recopiait 115308 du prompt sans appeler l'outil. La trace montre que Qwen appelle bien l'outil avec un code juste, mais sans `result = …`. |
| `analyst/sandbox.py` | **corrigé** | ajout de `last_expression_as_result` : la dernière expression est renvoyée comme dans un notebook. |
| `analyst/agent.py` | **prompt réécrit** | description de l'outil : « La valeur de la dernière ligne est renvoyée (ou celle de la variable `result`) » au lieu de « Mettez la réponse dans la variable `result` ». |
| `tests/test_sandbox.py` | ajouté | les 4 codes écrits par Qwen dans les traces deviennent des tests de régression. |
| `bench/results/summary_v1.md` | archivé | résultats avant correction, pour comparer avec la version 2. |

## Remarque

Le modèle seul réussit t01 parce que la description des données donne le nombre
de lignes : la tâche t01 l'avantage. Sans elle : 1 réussite sur 33.
