# Séance 02 — 2026-11-03 — guide de soutenance et interface web avec Claude Code

**Export de la conversation : À AJOUTER** (même conversation que la séance 01).

## Ce que j'ai demandé

- Un guide PDF pour préparer la soutenance (gardé hors du dépôt).
- Le choix de la démonstration.
- Une interface web locale pour présenter le projet (`python -m app`).

## Ce que l'IA a écrit, et ce qui a été corrigé

| fichier | statut | détail |
|---|---|---|
| `analyst/agent.py` | modifié | `ask(question, on_event=None)` : chaque étape est aussi envoyée à une fonction, pour que l'interface l'affiche en direct. Sans `on_event`, rien ne change (les tests d'avant passent). |
| `analyst/guard.py` | modifié | `find_numbers` garde la position de chaque nombre (les dates sont masquées par des espaces de même longueur au lieu d'un seul espace) ; `annotate` dit pour chaque chiffre de la réponse quel appel d'outil le justifie. |
| `analyst/sandbox.py` | **corrigé** | les captures d'écran montraient `np.float64(48.03)` : un scalaire numpy est maintenant converti en nombre Python (`48.03`). Test ajouté. |
| `app/server.py` | gardé tel quel | serveur `http.server` ; `/api/ask` envoie les étapes en *Server-Sent Events*. À relire. |
| `app/static/*` | **corrigé** | après captures : ligatures `==` désactivées dans le code, carte en double retirée en mode « modèle seul », valeurs écrites à côté des intervalles de confiance. |
| `tests/test_app.py` | **corrigé** | position attendue fausse dans mon test (le « 4 » de « Il y a 4 » est en position 7, pas 6). |

## Vérification

- `python -m pytest -q` : 68 tests.
- Interface vérifiée par captures d'écran avec un faux modèle (thème sombre et clair, mobile) ;
  à vérifier avec le vrai Qwen sur mon Mac.
