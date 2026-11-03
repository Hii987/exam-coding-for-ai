"""Affiche les échecs du benchmark, avec leur trace, pour les expliquer.

    python bench/show_failures.py                    # tous les échecs du mode système
    python bench/show_failures.py --tasks t01,t12    # seulement ces tâches
    python bench/show_failures.py --mode model_alone
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

RESULTS = Path(__file__).resolve().parent / "results"


def describe(row: dict, width: int = 300) -> str:
    """Résumé lisible d'une ligne de résultat : chaque étape, puis la réponse."""
    out = [f"=== {row['task']} | {row['mode']} lancement {row['run']} | statut : {row['status']} "
           f"| attendu : {row['expected']}"]
    for t in row.get("trace", []):
        if t["type"] == "llm":
            for c in t.get("tool_calls") or []:
                code = (c.get("arguments") or {}).get("code", "")
                out.append(f"  [{t['step']}] Qwen écrit du code :\n" +
                           "\n".join("        " + line for line in str(code).splitlines()))
            if not t.get("tool_calls") and t.get("content"):
                out.append(f"  [{t['step']}] Qwen répond : {t['content'][:width]}")
        elif t["type"] == "tool":
            tag = "BLOQUÉ" if t.get("blocked") else "sortie"
            out.append(f"  [{t['step']}] {tag} : {str(t['result'])[:width]}")
        elif t["type"] == "guard":
            verdict = "accepte" if t["ok"] else f"REFUSE {t['unsupported']}"
            out.append(f"  [{t['step']}] arbitre : {verdict}")
    out.append(f"  RÉPONSE FINALE : {row['answer'][:width]}")
    return "\n".join(out)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--mode", default="system")
    p.add_argument("--tasks", default="", help="ids séparés par des virgules")
    p.add_argument("--all", action="store_true", help="afficher aussi les réussites")
    p.add_argument("--dir", default=str(RESULTS), help="dossier des résultats")
    a = p.parse_args()
    results = Path(a.dir)
    wanted = set(a.tasks.split(",")) if a.tasks else None
    rows = []
    for path in sorted(results.glob(f"{a.mode}_run*.jsonl")):
        rows += [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows:
        raise SystemExit(f"Aucun fichier {a.mode}_run*.jsonl dans {results} : lancez d'abord run_bench.py")
    shown = [r for r in rows if (a.all or not r["correct"]) and (wanted is None or r["task"] in wanted)]
    for r in sorted(shown, key=lambda r: (r["task"], r["run"])):
        print(describe(r) + "\n")
    print(f"{len(shown)} ligne(s) affichée(s).")


if __name__ == "__main__":
    main()
