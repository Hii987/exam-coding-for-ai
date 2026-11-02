# Analyste de données avec arbitre — trajets Citi Bike

Projet final *Coding for AI & Data Science* (PGE3, 2026–2027).

Un petit agent répond en français à des questions sur les trajets en vélo en
libre-service Citi Bike de Jersey City et Hoboken (septembre 2024, données
ouvertes). Le modèle, **Qwen3.5-4B** (Q4_K_M, via Ollama), ne calcule rien de
tête : il écrit du code pandas que notre outil `run_pandas` exécute derrière une
barrière, puis **un arbitre écrit en Python refuse toute réponse qui contient un
chiffre qu'aucun calcul n'a produit**.

Briques choisies : **1** (outil), **3** (règles imposées par le code), **6**
(données sales, décisions écrites), **8** (incertitude), **9** (comparaison
mesurée). Les preuves sont dans [EVIDENCE.md](EVIDENCE.md).

## Installation (clone tout neuf)

Prérequis : Python 3.10+ et [Ollama](https://ollama.com).

```bash
git clone https://github.com/Hii987/exam-coding-for-ai.git
cd exam-coding-for-ai
python -m venv .venv
source .venv/bin/activate          # Windows : .venv\Scripts\activate
pip install -r requirements.txt
```

## 1. Les tests (aucun modèle ni téléchargement requis)

```bash
python -m pytest -q
```

## 2. Les données

```bash
python scripts/prepare_data.py
```

Télécharge `JC-202409-citibike-tripdata.csv.zip` (4 Mo) depuis
`s3.amazonaws.com/tripdata`, vérifie son empreinte SHA-256, le nettoie et écrit
le journal `data/cleaning_log.md`. Les données ne contiennent aucune donnée
personnelle (ni nom, ni identifiant d'usager).

## 3. Le modèle

```bash
ollama pull qwen3.5:4b-q4_K_M
```

Ollama doit tourner (`ollama serve`, ou l'application). Le contexte est fixé à
16 384 tokens (`num_ctx`) par le code ; changez-le avec `LLM_NUM_CTX=8192`.

## 4. Poser une question

```bash
python -m analyst "Combien de trajets ont commencé à Hoboken ?"
```

Affiche le code écrit par le modèle, le résultat de chaque appel, le verdict de
l'arbitre, la réponse, les tokens consommés, et sauve la trace dans `traces/`.
Options : `--no-tools` (le modèle seul), `--no-guard` (sans arbitre).

## 5. L'incertitude et le benchmark

```bash
python scripts/uncertainty.py
```

```bash
python bench/run_bench.py --runs 3
```

Le premier écrit `reports/uncertainty.md`. Le second lance les 12 tâches
3 fois en mode système et 3 fois en modèle seul, et écrit
`bench/results/summary.md` et les traces `bench/results/*.jsonl`.

## Si l'ordinateur ne fait pas tourner Qwen3.5-4B (Cerebras)

La clé reste dans une variable d'environnement, jamais dans le dépôt :

```bash
export CEREBRAS_API_KEY=...        # votre clé, à ne pas committer
export LLM_BACKEND=openai LLM_MODEL=qwen-3.8-27b
python bench/run_bench.py --runs 3 --sleep 13
```

`--sleep 13` respecte la limite de 5 requêtes par minute du compte gratuit.
Si vous utilisez Cerebras, indiquez-le ici : **modèle utilisé : à compléter**.

## Organisation

| fichier | rôle |
|---|---|
| `analyst/cleaning.py` | nettoyage + journal (brique 6) |
| `analyst/sandbox.py` | outil `run_pandas` et sa barrière AST (briques 1, 3) |
| `analyst/guard.py` | l'arbitre : aucun chiffre non calculé (brique 3) |
| `analyst/agent.py` | la boucle de l'agent et ses traces (brique 1) |
| `analyst/llm.py` | clients Ollama et OpenAI-compatible |
| `analyst/stats.py` | intervalles de confiance écrits à la main (brique 8) |
| `scripts/uncertainty.py` | rapport d'incertitude (brique 8) |
| `bench/` | tâches, réponses attendues, comparaison mesurée (brique 9) |
| `tests/` | tests pytest à réponse connue (R2) |
| `ai_log/` | journal d'usage de l'IA (R3) |

## Limites connues

- La barrière AST n'est pas un bac à sable de sécurité complet : elle bloque les
  chemins connus (imports, fichiers, attributs cachés, écriture pandas) et les
  tests montrent lesquels. Pour du code hostile, il faudrait un conteneur.
- L'arbitre vérifie que chaque nombre *a été calculé*, pas que c'est *le bon
  calcul* : un modèle qui calcule la mauvaise chose passe l'arbitre (voir
  l'échec expliqué dans EVIDENCE.md, brique 9).
- « 12,500 » est lu 12 500 (milliers), pas 12,5.
