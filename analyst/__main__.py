"""Poser une question : python -m analyst "Combien de trajets ont commencé à Hoboken ?" """
import argparse

from analyst import config
from analyst.agent import Agent, save_trace
from analyst.cleaning import load_clean
from analyst.llm import make_llm


def main() -> None:
    p = argparse.ArgumentParser(description="Analyste de données avec arbitre")
    p.add_argument("question")
    p.add_argument("--no-tools", action="store_true", help="le modèle seul, sans outil")
    p.add_argument("--no-guard", action="store_true", help="désactive l'arbitre")
    a = p.parse_args()
    if not config.CLEAN_CSV.exists():
        raise SystemExit("Données absentes : lancez d'abord python scripts/prepare_data.py")
    df = load_clean(config.CLEAN_CSV)
    agent = Agent(make_llm(), df, use_tools=not a.no_tools, use_guard=not a.no_guard)
    res = agent.ask(a.question)
    for t in res["trace"]:
        if t["type"] == "tool":
            print(f"--- run_pandas {'(BLOQUÉ)' if t['blocked'] else ''}\n{t['arguments'].get('code')}\n>>> {t['result'][:500]}")
        elif t["type"] == "guard":
            print(f"--- arbitre : {'OK' if t['ok'] else 'REFUS ' + str(t['unsupported'])}")
    print(f"\nRéponse ({res['status']}) : {res['answer']}")
    print(f"Tokens : {res['usage']}  |  {res['seconds']} s")
    print(f"Trace : {save_trace(res, config.TRACES_DIR)}")


if __name__ == "__main__":
    main()
