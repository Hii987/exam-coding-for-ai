# Résultats du benchmark

Modèle : `qwen3.5:4b-q4_K_M` (backend ollama), température 0.7, 12 tâches.

| mode | lancements | exactitude moyenne | écart-type | par lancement | refus | tokens moyens / tâche |
|---|---|---|---|---|---|---|
| model_alone | 3 | 8.3% | 0.0% | 8%, 8%, 8% | 0 | 364 |
| system | 3 | 91.7% | 0.0% | 92%, 92%, 92% | 1 | 1691 |

## Par tâche (réussites / lancements)

| tâche | attendu | model_alone | system |
|---|---|---|---|
| t01 | 115308.0 | 3/3 | 3/3 |
| t02 | 73.8908 | 0/3 | 3/3 |
| t03 | 9.7812 | 0/3 | 3/3 |
| t04 | 6.1706 | 0/3 | 3/3 |
| t05 | Hoboken Terminal - River St & Hudson Pl | 0/3 | 3/3 |
| t06 | 83.0 | 0/3 | 3/3 |
| t07 | 55380.0 | 0/3 | 3/3 |
| t08 | 2024-09-13 | 0/3 | 0/3 |
| t09 | 6.3521 | 0/3 | 3/3 |
| t10 | 68.9829 | 0/3 | 3/3 |
| t11 | 17.0 | 0/3 | 3/3 |
| t12 | 321.0 | 0/3 | 3/3 |
