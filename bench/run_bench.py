"""Comparaison mesurée (brique 9) : le système (outil + arbitre) face au modèle seul.

    python bench/run_bench.py --runs 3              # les deux modes, 3 lancements
    python bench/run_bench.py --runs 3 --sleep 13   # Cerebras : 5 requêtes / minute

Écrit chaque trace dans bench/results/<mode>_run<k>.jsonl et le résumé
(moyenne, écart-type) dans bench/results/summary.md.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from analyst import config, guard  # noqa: E402
from analyst.agent import Agent  # noqa: E402
from analyst.cleaning import load_clean  # noqa: E402
from bench.tasks import TASKS, compute_expected  # noqa: E402

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
EXPECTED = HERE / "expected.json"


def score(answer: str, expected, kind: str, tol: float = 0.0) -> bool:
    """Vrai si la réponse contient la valeur attendue (à la tolérance près)."""
    if kind == "text":
        return str(expected).lower() in answer.lower()
    for _, v, _ in guard.extract_numbers(answer):
        for cand in (v, v * 100):  # 0,738 accepté pour 73,8 %
            if tol == 0 and cand == expected:
                return True
            if tol > 0 and abs(cand - expected) <= tol * abs(expected):
                return True
    return False


def summarize(rows: list[dict]) -> str:
    modes = sorted({r["mode"] for r in rows})
    lines = ["# Résultats du benchmark", "",
             f"Modèle : `{config.MODEL}` (backend {config.BACKEND}), "
             f"température {config.TEMPERATURE}, {len(TASKS)} tâches.", "",
             "| mode | lancements | exactitude moyenne | écart-type | par lancement | refus | tokens moyens / tâche |",
             "|---|---|---|---|---|---|---|"]
    for m in modes:
        runs = sorted({r["run"] for r in rows if r["mode"] == m})
        accs = [statistics.mean(r["correct"] for r in rows if r["mode"] == m and r["run"] == k)
                for k in runs]
        sd = statistics.stdev(accs) if len(accs) > 1 else 0.0
        refus = sum(r["status"] == "refused" for r in rows if r["mode"] == m)
        toks = statistics.mean(r["tokens"] for r in rows if r["mode"] == m)
        lines.append(f"| {m} | {len(runs)} | {statistics.mean(accs):.1%} | {sd:.1%} | "
                     f"{', '.join(f'{a:.0%}' for a in accs)} | {refus} | {toks:.0f} |")
    lines += ["", "## Par tâche (réussites / lancements)", "",
              "| tâche | attendu | " + " | ".join(modes) + " |",
              "|---|---|" + "---|" * len(modes)]
    for t in TASKS:
        if not any(r["task"] == t["id"] for r in rows):
            continue  # tâche non lancée (option --tasks)
        cells = []
        for m in modes:
            rs = [r for r in rows if r["mode"] == m and r["task"] == t["id"]]
            cells.append(f"{sum(r['correct'] for r in rs)}/{len(rs)}")
        exp = next(r["expected"] for r in rows if r["task"] == t["id"])
        lines.append(f"| {t['id']} | {exp} | " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--runs", type=int, default=3)
    p.add_argument("--modes", default="system,model_alone")
    p.add_argument("--sleep", type=float, default=0.0, help="pause entre tâches (s)")
    p.add_argument("--tasks", default="", help="ids séparés par des virgules (défaut : toutes)")
    p.add_argument("--out", default=str(RESULTS),
                   help="dossier des résultats (pour ne pas écraser bench/results)")
    a = p.parse_args()
    out_dir = Path(a.out)

    from analyst.llm import make_llm
    df = load_clean(config.CLEAN_CSV)
    expected = compute_expected(df)
    frozen = json.loads(EXPECTED.read_text()) if EXPECTED.exists() else None
    if frozen and frozen != expected:
        print("ATTENTION : les réponses attendues diffèrent de bench/expected.json")
    llm = make_llm()
    tasks = [t for t in TASKS if not a.tasks or t["id"] in a.tasks.split(",")]
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for mode in a.modes.split(","):
        agent = Agent(llm, df, use_tools=(mode == "system"))
        for k in range(1, a.runs + 1):
            path = out_dir / f"{mode}_run{k}.jsonl"
            with path.open("w", encoding="utf-8") as f:
                for t in tasks:
                    try:
                        res = agent.ask(t["question"])
                    except Exception as e:  # serveur coupé, quota... : compté comme échec
                        res = {"answer": "", "status": f"error: {e}", "trace": [],
                               "usage": {"prompt_tokens": 0, "completion_tokens": 0}}
                    ok = score(res["answer"], expected[t["id"]], t["kind"], t.get("tol", 0))
                    row = {"mode": mode, "run": k, "task": t["id"], "expected": expected[t["id"]],
                           "answer": res["answer"], "status": res["status"], "correct": ok,
                           "tokens": sum(res["usage"].values())}
                    rows.append(row)
                    f.write(json.dumps({**row, "trace": res["trace"]}, ensure_ascii=False,
                                       default=str) + "\n")
                    print(f"[{mode} run{k}] {t['id']} {'OK ' if ok else 'NON'} {res['answer'][:90]!r}")
                    time.sleep(a.sleep)
    summary = summarize(rows)
    (out_dir / "summary.md").write_text(summary, encoding="utf-8")
    print("\n" + summary)


if __name__ == "__main__":
    main()
