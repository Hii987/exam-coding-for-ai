# EVIDENCE — une section par brique

Toutes les commandes se lancent depuis la racine du dépôt, après l'installation
du README. Les sections marquées **À COMPLÉTER** demandent une exécution avec
Qwen3.5-4B sur ma machine (le modèle n'a pas pu tourner dans l'environnement où
le code a été écrit).

---

## Brique 1 — Notre propre outil : `run_pandas`

**Ce que je montre.** Une fonction écrite par moi, `sandbox.run_code`, exposée au
modèle sous le nom `run_pandas` (schéma dans `analyst/agent.py`, `TOOLS`). Le
modèle envoie du code, l'outil l'exécute sur le DataFrame et renvoie le résultat ;
la boucle (`Agent.ask`) recommence jusqu'à la réponse finale.

**Fichiers.** `analyst/sandbox.py`, `analyst/agent.py`, `tests/test_agent.py`.

**Reproduire.**

```bash
python -m analyst "Combien de trajets ont commencé à Hoboken ?"
```

**Trace d'un vrai appel** (Qwen3.5-4B Q4_K_M via Ollama, sur mon Mac, 2026-11-02) :

```
$ python -m analyst "Combien de trajets ont commencé à Hoboken ?"
--- run_pandas
result = df[df['start_city'] == 'Hoboken'].shape[0]
>>> 55380
--- arbitre : OK

Réponse (answered) : 55 380 trajets ont commencé à Hoboken.
Tokens : {'prompt_tokens': 1357, 'completion_tokens': 60}  |  35.48 s
```

Fichier de trace complet : `ai_log/traces/trace_20261102_124635_306260.json`
(copié depuis `traces/`).

Lecture de la trace : le modèle n'a pas répondu de tête, il a appelé l'outil une
fois ; l'outil a renvoyé `55380` ; l'arbitre a retrouvé « 55 380 » (écrit avec
une espace) dans cette sortie et a laissé passer la réponse. Coût : 1 417 tokens.

Réponse attendue : 55 380 trajets (`bench/expected.json`, t07) : **juste**.

---

## Brique 3 — Deux règles imposées par le code

**Règle 1 : le code du modèle ne touche jamais au système.** Avant exécution,
`sandbox.check_code` parcourt l'arbre syntaxique et refuse imports, `open`,
`eval`, attributs commençant par `_`, écritures/lectures pandas (`to_csv`,
`read_*`)… Le code refusé n'est **jamais exécuté**.

**Règle 2 : aucun chiffre non calculé dans la réponse.** `guard.check_answer`
extrait chaque nombre et chaque date de la réponse et exige qu'ils figurent dans
les sorties réussies de `run_pandas` (ou dans la question). Sinon l'agent renvoie
la réponse au modèle ; après 2 refus, le système répond qu'il ne peut pas donner
de chiffre vérifié. Le prompt *demande* la même chose, mais c'est le code qui
*l'impose* : `test_guard_refuses_after_retries` montre un modèle qui insiste et
se fait refuser.

**Tests qui essaient d'enfreindre les règles.** `tests/test_sandbox.py`
(13 attaques : `import os`, `open('/etc/passwd')`, `df.to_csv`,
`().__class__.__bases__[0].__subclasses__()`, `pd.io.common.os.system`… toutes
bloquées, aucun fichier écrit) et `tests/test_guard.py`, `tests/test_agent.py`.

```bash
python -m pytest -q tests/test_sandbox.py tests/test_guard.py tests/test_agent.py
```

**En vrai — À COMPLÉTER** : une question qui pousse le modèle à inventer, par
exemple :

```bash
python -m analyst "Combien de trajets y aura-t-il en octobre 2024 ?"
```

---

## Brique 6 — Données sales, décisions écrites

**Données.** Trajets Citi Bike, Jersey City + Hoboken, septembre 2024 :
115 558 lignes brutes, données ouvertes publiées par Lyft/Citi Bike
(`s3.amazonaws.com/tripdata`). Le script vérifie l'empreinte SHA-256.

**Journal de nettoyage.** `data/cleaning_log.md` (généré) :

| étape | retirées | modifiées | source de la règle |
|---|---|---|---|
| doublons `ride_id` | 0 | | décision |
| dates illisibles (texte -> datetime) | 0 | 231 116 valeurs converties | décision |
| durée ≤ 0 | 0 | | décision |
| durée < 60 s | 0 | | **document** : page *System Data* de Citi Bike |
| durée > 24 h | **27** | | **document** : règles de location Citi Bike |
| id de station d'arrivée reconstitué à partir du nom | 0 | **30** libellés corrigés | décision |
| station d'arrivée manquante (vélo non redéposé) | **223** | | décision |
| ville déduite de l'id de station | 0 | 230 616 | **document** + vérification sur les coordonnées |

Résultat : **115 308 trajets propres**.

**Règles que le fichier ne dit pas, et de qui elles viennent.**

1. *« Les trajets de moins de 60 secondes ont été retirés (faux départs ou
   re-dépôt du vélo), ainsi que ceux du personnel et des stations de test. »* —
   Citi Bike, page **System Data**, https://citibikenyc.com/system-data. Je
   vérifie que c'est bien le cas : 0 trajet de moins de 60 s dans le fichier.
2. *« Un vélo non rendu au bout de 24 heures est considéré comme perdu ou
   volé. »* — Citi Bike, règles de location. → les 27 « trajets » de plus de
   24 h (jusqu'à 6 jours) ne sont pas des trajets.
   **À VÉRIFIER : retrouver la phrase exacte et son URL**, ou remplacer par une
   règle obtenue auprès d'une personne (nommer qui).
3. *Les ids `HBxxx` sont à Hoboken, `JCxxx` à Jersey City, et les ids numériques
   (ex. `6432.11`, « E 40 St & Park Ave ») sont des stations de **Manhattan**.*
   Découverte pendant le nettoyage : 321 trajets traversent l'Hudson. Première
   version : retirés comme « préfixe inconnu ». Après lecture des noms et des
   coordonnées : gardés, avec `end_city = "New York"`.

```bash
python scripts/prepare_data.py
python -m pytest -q tests/test_cleaning.py
```

---

## Brique 8 — Des chiffres avec leur incertitude

**Ce que je montre.** Une comparaison A/B observationnelle abonnés / occasionnels,
avec des intervalles de confiance écrits à la main (`analyst/stats.py` : IC normal
de la moyenne, bootstrap percentile, Wilson pour une proportion, différences).
Extrait de `reports/uncertainty.md` :

- durée moyenne, abonnés : 8,12 min [8,03 ; 8,21] ; occasionnels : 14,47 min [14,14 ; 14,80]
- différence occasionnels − abonnés : **6,35 min [6,01 ; 6,69]**
- part des vélos électriques : abonnés 54,23 % [53,90 ; 54,57], occasionnels 68,98 % [68,46 ; 69,50]

**Ce que les données ne permettent pas de conclure.** Ce n'est pas un test A/B
randomisé : on ne peut pas dire qu'être abonné *raccourcit* un trajet. Et le
fichier n'a pas d'identifiant d'usager : un même abonné fait beaucoup de trajets,
ils ne sont pas indépendants, donc les intervalles ci-dessus sont **trop étroits**.

```bash
python scripts/uncertainty.py
python -m pytest -q tests/test_stats.py
```

Les fonctions sont aussi données au modèle (`stats.mean_ci`, …) dans `run_pandas`.

---

## Brique 9 — Une comparaison mesurée

**Protocole.** 12 tâches (`bench/tasks.py`) dont la réponse est calculée par du
code de référence écrit à la main et figée dans `bench/expected.json`. Deux
modes, même modèle Qwen3.5-4B, température 0,7 : **système** (outil + arbitre)
contre **modèle seul** (même schéma des données, pas d'outil). 3 lancements
chacun. Une réponse est juste si elle contient la valeur attendue (exacte pour
un entier, à 1 % près pour un décimal, texte exact pour une station ou une
date). Un refus de l'arbitre compte comme faux.

```bash
python bench/run_bench.py --runs 3
```

**Résultats, version 1** (Qwen3.5-4B Q4_K_M via Ollama, sur mon Mac, 3 novembre 2026 ;
détail par tâche dans `bench/results/summary_v1.md`) :

| mode | lancements | exactitude moyenne | écart-type | par lancement | refus de l'arbitre | tokens / tâche |
|---|---|---|---|---|---|---|
| système (outil + arbitre) | 3 | **52,8 %** | 19,2 pts | 75 %, 42 %, 42 % | 10 | 4 422 |
| modèle seul | 3 | 11,1 % | 4,8 pts | 8 %, 8 %, 17 % | 0 | 366 |

**Lecture.** Le système fait presque 5 fois mieux que le modèle seul (+41,7 points),
pour environ 12 fois plus de tokens. Il est aussi beaucoup plus variable
(écart-type de 19,2 points : un lancement à 75 %, deux à 42 %), et 10 de ses
réponses ont été refusées par l'arbitre, ce qui compte comme faux.

**Une anomalie à expliquer : t01.** Le modèle seul réussit « Combien de trajets
y a-t-il ? » 3 fois sur 3. Ce n'est pas qu'il devine bien : la description des
données qu'il reçoit commence par « DataFrame `df` : 115308 trajets ». Il recopie
le prompt. La tâche t01 avantage donc le modèle seul, et sans elle, il ne
réussit que 1 réponse sur 33.

**Un échec expliqué à partir de sa trace : t12 et t01.** Commande :
`python bench/show_failures.py --tasks t01,t12` ; sortie complète gardée dans
`ai_log/traces/bench_v1_echecs_t01_t12.txt`.

Extrait (t12, « Combien de trajets se terminent à New York ? », attendu 321,
lancement 2) :

```
[0] Qwen écrit du code :  (df[df['end_city'] == 'New York']['ride_id'].count())
[0] sortie : (rien : assignez votre réponse à la variable `result`)
[1] Qwen répond : Il y a 26450 trajets se terminant à New York.
[1] arbitre : REFUSE ['26450']
... deux fois encore ...
RÉPONSE FINALE : Je ne peux pas donner de réponse chiffrée vérifiée ...
```

Lecture de la trace, étape par étape :

1. **Le code de Qwen est juste.** Le filtre `end_city == 'New York'` puis le
   comptage donnent bien 321. Le modèle a compris la question et la colonne.
2. **Mon outil ne renvoie rien.** Qwen écrit le calcul comme dans un notebook,
   sans `result = …`. Or `run_pandas` ne renvoyait que la variable `result` :
   la sortie est « (rien : assignez votre réponse à la variable `result`) ».
3. **Qwen n'a aucun chiffre, et il en invente un** : 26450 (et dans les autres
   lancements 12 465,38, 10834, 13478, 0). Il ne comprend pas l'indication et
   réécrit le même code trois fois.
4. **L'arbitre refuse chaque chiffre inventé**, trois fois, puis le système
   répond qu'il ne peut pas donner de chiffre vérifié. La réponse est comptée
   fausse, mais **aucun chiffre faux n'a été donné** à l'utilisateur.

**Diagnostic.** La faute n'est ni au modèle ni à l'arbitre, mais à la
convention de mon outil (`result = …`), peu naturelle pour un modèle habitué
aux notebooks. Les 5 échecs de t01 et t12 ont la même cause. Le cas t01 montre
aussi une **fausse alerte** de l'arbitre : au lancement 3, Qwen recopie le bon
nombre (115308) depuis la description des données, et l'arbitre le refuse,
car le prompt ne compte pas comme une preuve. C'est voulu : un chiffre doit
venir d'un calcul de la session.

**Correction.** `sandbox.last_expression_as_result` : comme dans un notebook, si
le code n'affecte jamais `result` et finit par une expression, sa valeur est
renvoyée. La description de l'outil le dit au modèle. Les codes écrits par Qwen
dans ces traces sont rejoués dans `tests/test_sandbox.py`
(`test_last_expression_is_returned_like_a_notebook`), et un test vérifie que la
barrière s'applique toujours.

**Résultats, version 2 (après correction)** (mêmes conditions : Qwen3.5-4B,
température 0,7, 12 tâches, 3 lancements ; détail dans `bench/results/summary.md`) :

| mode | exactitude moyenne | écart-type | par lancement | refus de l'arbitre | tokens / tâche |
|---|---|---|---|---|---|
| système (outil + arbitre) | **91,7 %** | 0,0 pt | 92 %, 92 %, 92 % | 1 | 1 691 |
| modèle seul | 8,3 % | 0,0 pt | 8 %, 8 %, 8 % | 0 | 364 |

**Avant / après la correction (mode système).**

| | version 1 | version 2 |
|---|---|---|
| exactitude moyenne | 52,8 % | **91,7 %** |
| écart-type entre lancements | 19,2 pts | **0,0 pt** |
| refus de l'arbitre | 10 | **1** |
| tokens par tâche | 4 422 | **1 691** |
| t01 / t12 | 1/3 et 0/3 | **3/3 et 3/3** |

La correction d'une seule convention de l'outil fait gagner 39 points, rend le
système stable d'un lancement à l'autre, et divise par 2,6 le nombre de tokens
(Qwen ne réécrit plus trois fois le même code). Le modèle seul reste à 8,3 % :
il ne réussit que t01, grâce au nombre de lignes donné dans le prompt.

Limite : 3 lancements de 12 tâches, c'est peu. Un écart-type de 0 veut dire que
les 3 lancements ont donné le même score, pas que le système est parfaitement
stable ; avec plus de tâches ou de lancements, on verrait sans doute de la variation.

**Échec restant en version 2 : t08 (jour le plus chargé) — À COMPLÉTER** à partir
de `python bench/show_failures.py --tasks t08`.
