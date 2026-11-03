"""La boucle de l'agent (brique 1 : notre propre outil `run_pandas`).

1. Le modèle reçoit la question et le schéma des données.
2. Il appelle `run_pandas` autant de fois que nécessaire (max MAX_STEPS).
3. Sa réponse finale passe devant l'arbitre (guard.check_answer). Un chiffre
   non calculé -> la réponse est renvoyée au modèle ; après MAX_RETRIES refus,
   le système répond qu'il ne peut pas donner de chiffre vérifié.
Chaque étape est écrite dans la trace (liste de dicts, sauvegardable en JSON).
"""
from __future__ import annotations

import json
import re
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

from analyst import guard, sandbox

MAX_STEPS = 8
MAX_RETRIES = 2
REFUSAL = ("Je ne peux pas donner de réponse chiffrée vérifiée : les chiffres proposés "
           "n'ont pas été calculés par le code.")

TOOLS = [{
    "type": "function",
    "function": {
        "name": "run_pandas",
        "description": (
            "Exécute du code Python sur le DataFrame `df` (trajets Citi Bike nettoyés). "
            "`pd`, `np` et `stats` (mean_ci, bootstrap_ci, diff_means_ci, prop_ci, "
            "diff_props_ci) sont disponibles. Aucun import. Mettez la réponse dans la "
            "variable `result`."),
        "parameters": {
            "type": "object",
            "properties": {"code": {"type": "string", "description": "code Python"}},
            "required": ["code"],
        },
    },
}]


def schema_text(df: pd.DataFrame) -> str:
    cols = ", ".join(f"{c} ({t})" for c, t in df.dtypes.astype(str).items())
    return (f"DataFrame `df` : {len(df)} trajets Citi Bike de Jersey City et Hoboken, "
            f"septembre 2024, déjà nettoyés. Colonnes : {cols}. "
            "duration_min = durée en minutes ; member_casual vaut 'member' ou 'casual' ; "
            "rideable_type vaut 'electric_bike' ou 'classic_bike' ; start_city vaut 'Hoboken' ou "
            "'Jersey City', end_city aussi ou 'New York' ; round_trip = départ et arrivée à la même station.")


SYSTEM_PROMPT = """Tu es un analyste de données. Réponds en français.
{schema}
Règle : tout chiffre de ta réponse doit venir d'un appel à l'outil run_pandas.
Calcule d'abord avec run_pandas, puis réponds en une ou deux phrases en recopiant
les chiffres obtenus (arrondis au plus à 2 décimales)."""

BASELINE_PROMPT = """Tu es un analyste de données. Réponds en français.
{schema}
Tu n'as pas accès aux données ni à aucun outil. Donne ta meilleure estimation
chiffrée en une ou deux phrases."""


def strip_think(text: str) -> str:
    return re.sub(r"<think>.*?</think>", "", text or "", flags=re.S).strip()


class Agent:
    def __init__(self, llm, df: pd.DataFrame, use_tools: bool = True, use_guard: bool = True):
        self.llm, self.df = llm, df
        self.use_tools, self.use_guard = use_tools, use_guard and use_tools

    def ask(self, question: str, on_event=None) -> dict:
        """Pose la question. `on_event(ev)` (facultatif) reçoit chaque étape en direct :
        c'est ce qui permet à l'interface web d'afficher la boucle pendant qu'elle tourne."""
        t0 = time.time()
        prompt = SYSTEM_PROMPT if self.use_tools else BASELINE_PROMPT
        messages = [{"role": "system", "content": prompt.format(schema=schema_text(self.df))},
                    {"role": "user", "content": question}]
        trace: list[dict] = []
        tool_outputs: list[str] = []
        usage = {"prompt_tokens": 0, "completion_tokens": 0}
        retries = 0
        answer, status = "", "max_steps"

        def log(ev: dict) -> None:
            trace.append(ev)
            if on_event:
                on_event(ev)

        for step in range(MAX_STEPS):
            if on_event:
                on_event({"step": step, "type": "thinking"})
            reply = self.llm.chat(messages, TOOLS if self.use_tools else None)
            for k in usage:
                usage[k] += reply.get("usage", {}).get(k, 0) or 0
            content = strip_think(reply["content"])
            calls = reply["tool_calls"] if self.use_tools else []
            log({"step": step, "type": "llm", "content": content,
                          "tool_calls": calls})

            if calls:
                messages.append({"role": "assistant", "content": content, "tool_calls": calls})
                for c in calls:
                    if c["name"] != "run_pandas":
                        res = {"ok": False, "output": "", "error": f"outil inconnu {c['name']}"}
                    else:
                        res = sandbox.run_code(str(c["arguments"].get("code", "")), self.df)
                    text = res["output"] or ""
                    if res.get("stdout"):
                        text = (res["stdout"] + "\n" + text).strip()
                    if res["error"]:
                        text = f"ERREUR : {res['error']}"
                    else:
                        tool_outputs.append(text)
                    log({"step": step, "type": "tool", "name": c["name"],
                                  "arguments": c["arguments"], "result": text,
                                  "blocked": res.get("blocked", False)})
                    messages.append({"role": "tool", "content": text, "name": c["name"],
                                     "tool_call_id": c["id"]})
                continue

            # réponse finale
            if not self.use_guard:
                answer, status = content, "answered"
                break
            verdict = guard.check_answer(content, tool_outputs, question)
            log({"step": step, "type": "guard", "answer": content, **verdict})
            if verdict["ok"]:
                answer, status = content, "answered"
                break
            retries += 1
            if retries > MAX_RETRIES:
                answer, status = REFUSAL, "refused"
                break
            messages.append({"role": "assistant", "content": content})
            messages.append({"role": "user", "content": (
                "ARBITRE : ces chiffres n'ont été calculés par aucun appel à run_pandas : "
                f"{', '.join(verdict['unsupported'])}. Calcule-les avec run_pandas, "
                "ou retire-les de ta réponse.")})
        else:
            answer = REFUSAL if self.use_guard else answer

        return {"question": question, "answer": answer, "status": status, "trace": trace,
                "usage": usage, "seconds": round(time.time() - t0, 2),
                "mode": "system" if self.use_tools else "model_alone"}


def save_trace(result: dict, directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"trace_{datetime.now():%Y%m%d_%H%M%S_%f}.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str),
                    encoding="utf-8")
    return path
