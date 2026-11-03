"""Serveur web local de l'interface (bibliothèque standard uniquement).

    python -m app              ->  http://127.0.0.1:8000

Routes :
    GET  /                    l'interface (app/static/index.html)
    GET  /api/status          modèle, Ollama joignable ?, données chargées ?
    GET  /api/examples        les questions du benchmark (puces d'exemples)
    GET  /api/ask?q=&mode=    la boucle de l'agent EN DIRECT (Server-Sent Events)
    POST /api/sandbox         la barrière seule : {"code"} -> bloqué ou résultat
    POST /api/guard           l'arbitre seul : {"answer", "outputs", "question"} -> chiffres annotés
    GET  /api/bench           les résultats de bench/results/*.jsonl
    GET  /api/bench/trace     la trace d'une case du benchmark
    GET  /api/data            journal de nettoyage + intervalles de confiance
"""
from __future__ import annotations

import json
import mimetypes
import statistics
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests

from analyst import config, guard, sandbox, stats
from analyst.agent import Agent, save_trace
from bench.run_bench import score
from bench.tasks import TASKS

STATIC = Path(__file__).resolve().parent / "static"


class ClientGone(Exception):
    """Le navigateur a fermé la connexion : on arrête la boucle de l'agent."""


class App:
    """L'état du serveur : les données, la fabrique du modèle, les chemins."""

    def __init__(self, df, llm_factory, results_dir: Path, expected_path: Path,
                 cleaning_log: Path, traces_dir: Path | None = config.TRACES_DIR):
        self.df, self.llm_factory = df, llm_factory
        self.results_dir, self.expected_path = results_dir, expected_path
        self.cleaning_log, self.traces_dir = cleaning_log, traces_dir
        self._uncertainty = None
        self._lock = threading.Lock()

    # ---------- état ----------
    def status(self) -> dict:
        info = {"model": config.MODEL, "backend": config.BACKEND, "num_ctx": config.NUM_CTX,
                "rows": int(len(self.df)), "llm_ok": None, "llm_detail": ""}
        if config.BACKEND == "ollama":
            try:
                r = requests.get(f"{config.OLLAMA_URL}/api/tags", timeout=1.5)
                names = [m.get("name", "") for m in r.json().get("models", [])]
                info["llm_ok"] = config.MODEL in names
                info["llm_detail"] = ("modèle prêt" if info["llm_ok"]
                                      else f"Ollama répond, mais {config.MODEL} n'est pas installé")
            except Exception:
                info["llm_ok"], info["llm_detail"] = False, "Ollama ne répond pas"
        else:
            info["llm_ok"], info["llm_detail"] = True, "API compatible OpenAI"
        return info

    def expected(self) -> dict:
        if self.expected_path.exists():
            return json.loads(self.expected_path.read_text(encoding="utf-8"))
        return {}

    def examples(self) -> list[dict]:
        exp = self.expected()
        return [{"id": t["id"], "question": t["question"], "expected": exp.get(t["id"])}
                for t in TASKS]

    # ---------- l'agent en direct ----------
    def ask(self, question: str, mode: str, emit) -> None:
        agent = Agent(self.llm_factory(), self.df, use_tools=(mode == "system"))
        emit({"type": "start", "mode": mode, "question": question})
        res = agent.ask(question, on_event=emit)
        outputs = [t["result"] for t in res["trace"]
                   if t["type"] == "tool" and not t["result"].startswith("ERREUR")]
        done = {"type": "done", "mode": mode, "answer": res["answer"], "status": res["status"],
                "usage": res["usage"], "seconds": res["seconds"],
                "spans": guard.annotate(res["answer"], outputs, question)}
        task = next((t for t in TASKS if t["question"].strip() == question.strip()), None)
        exp = self.expected()
        if task and task["id"] in exp:
            done["expected"] = exp[task["id"]]
            done["correct"] = score(res["answer"], exp[task["id"]], task["kind"], task.get("tol", 0))
        if self.traces_dir is not None:
            done["trace_path"] = str(save_trace(res, self.traces_dir))
        emit(done)

    # ---------- barrière et arbitre seuls ----------
    def run_sandbox(self, code: str) -> dict:
        try:
            sandbox.check_code(code)
        except sandbox.Blocked as e:
            return {"ok": False, "blocked": True, "reason": str(e), "output": "", "error": None}
        res = sandbox.run_code(code, self.df)
        return {**res, "reason": None}

    @staticmethod
    def run_guard(answer: str, outputs: list[str], question: str = "") -> dict:
        verdict = guard.check_answer(answer, outputs, question)
        return {**verdict, "spans": guard.annotate(answer, outputs, question)}

    # ---------- benchmark ----------
    def _bench_rows(self) -> list[dict]:
        rows = []
        for path in sorted(self.results_dir.glob("*_run*.jsonl")):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    rows.append(json.loads(line))
        return rows

    def bench(self) -> dict:
        rows = self._bench_rows()
        if not rows:
            return {"available": False}
        questions = {t["id"]: t["question"] for t in TASKS}
        modes = {}
        for m in sorted({r["mode"] for r in rows}):
            runs = sorted({r["run"] for r in rows if r["mode"] == m})
            accs = [statistics.mean(r["correct"] for r in rows if r["mode"] == m and r["run"] == k)
                    for k in runs]
            mrows = [r for r in rows if r["mode"] == m]
            modes[m] = {"runs": runs, "per_run": accs, "mean": statistics.mean(accs),
                        "sd": statistics.stdev(accs) if len(accs) > 1 else 0.0,
                        "refused": sum(r["status"] == "refused" for r in mrows),
                        "tokens": statistics.mean(r.get("tokens", 0) for r in mrows)}
        cells = [{"mode": r["mode"], "run": r["run"], "task": r["task"], "correct": r["correct"],
                  "answer": r["answer"], "status": r["status"], "expected": r["expected"]}
                 for r in rows]
        tasks = [{"id": t, "question": questions.get(t, t)}
                 for t in sorted({r["task"] for r in rows})]
        return {"available": True, "modes": modes, "cells": cells, "tasks": tasks}

    def bench_trace(self, mode: str, run: int, task: str) -> dict | None:
        for r in self._bench_rows():
            if r["mode"] == mode and r["run"] == run and r["task"] == task:
                return r
        return None

    # ---------- données ----------
    def data(self) -> dict:
        log = (json.loads(self.cleaning_log.read_text(encoding="utf-8"))
               if self.cleaning_log.exists() else {"rules": {}, "steps": []})
        with self._lock:
            if self._uncertainty is None:
                self._uncertainty = self._compute_uncertainty()
        return {"log": log, "uncertainty": self._uncertainty}

    def _compute_uncertainty(self) -> dict:
        import numpy as np
        df = self.df
        mem = df[df.member_casual == "member"]
        cas = df[df.member_casual == "casual"]

        def elec(g):
            return stats.prop_ci(int((g.rideable_type == "electric_bike").sum()), len(g))

        def sample(g):
            return g.duration_min.sample(min(20000, len(g)), random_state=0)

        k1 = int((cas.rideable_type == "electric_bike").sum())
        k2 = int((mem.rideable_type == "electric_bike").sum())
        return {
            "n": {"member": int(len(mem)), "casual": int(len(cas))},
            "mean": {"member": stats.mean_ci(mem.duration_min),
                     "casual": stats.mean_ci(cas.duration_min)},
            "median": {"member": stats.bootstrap_ci(sample(mem), np.median, n_boot=1000),
                       "casual": stats.bootstrap_ci(sample(cas), np.median, n_boot=1000)},
            "diff_mean": stats.diff_means_ci(cas.duration_min, mem.duration_min),
            "electric": {"member": elec(mem), "casual": elec(cas)},
            "diff_electric": stats.diff_props_ci(k1, len(cas), k2, len(mem)),
        }


def make_handler(app: App):
    class Handler(BaseHTTPRequestHandler):
        server_version = "Arbitre/1.0"

        def log_message(self, fmt, *args):  # silencieux pendant la démo
            pass

        # ----- réponses -----
        def _json(self, obj, code: int = 200) -> None:
            body = json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _static(self, rel: str) -> None:
            path = (STATIC / rel).resolve()
            if STATIC not in path.parents and path != STATIC or not path.is_file():
                return self._json({"error": "introuvable"}, 404)
            body = path.read_bytes()
            ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            self.send_response(200)
            self.send_header("Content-Type", f"{ctype}; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _body(self) -> dict:
            n = int(self.headers.get("Content-Length", 0) or 0)
            return json.loads(self.rfile.read(n) or b"{}")

        # ----- routes -----
        def do_GET(self):
            url = urlparse(self.path)
            q = {k: v[0] for k, v in parse_qs(url.query).items()}
            if url.path in ("/", "/index.html"):
                return self._static("index.html")
            if url.path.startswith("/static/"):
                return self._static(url.path[len("/static/"):])
            if url.path == "/api/status":
                return self._json(app.status())
            if url.path == "/api/examples":
                return self._json(app.examples())
            if url.path == "/api/bench":
                return self._json(app.bench())
            if url.path == "/api/bench/trace":
                r = app.bench_trace(q.get("mode", ""), int(q.get("run", 0)), q.get("task", ""))
                return self._json(r or {"error": "introuvable"}, 200 if r else 404)
            if url.path == "/api/data":
                return self._json(app.data())
            if url.path == "/api/ask":
                return self._stream(q.get("q", "").strip(), q.get("mode", "system"))
            return self._json({"error": "introuvable"}, 404)

        def do_POST(self):
            url = urlparse(self.path)
            try:
                body = self._body()
            except json.JSONDecodeError:
                return self._json({"error": "JSON invalide"}, 400)
            if url.path == "/api/sandbox":
                return self._json(app.run_sandbox(str(body.get("code", ""))))
            if url.path == "/api/guard":
                return self._json(app.run_guard(str(body.get("answer", "")),
                                                [str(o) for o in body.get("outputs", [])],
                                                str(body.get("question", ""))))
            return self._json({"error": "introuvable"}, 404)

        def _stream(self, question: str, mode: str) -> None:
            """Server-Sent Events : une ligne `data: {...}` par étape de l'agent."""
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "close")
            self.end_headers()
            self.close_connection = True

            def emit(ev: dict) -> None:
                try:
                    data = json.dumps(ev, ensure_ascii=False, default=str)
                    self.wfile.write(f"data: {data}\n\n".encode("utf-8"))
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError) as e:
                    raise ClientGone() from e

            if not question:
                return emit({"type": "error", "message": "question vide"})
            if mode not in ("system", "model_alone"):
                return emit({"type": "error", "message": f"mode inconnu : {mode}"})
            try:
                app.ask(question, mode, emit)
            except ClientGone:
                return
            except requests.ConnectionError:
                self._safe(emit, {"type": "error", "message":
                                  "Ollama ne répond pas : ouvrez Ollama puis réessayez."})
            except Exception as e:  # erreur du modèle ou du serveur : on l'affiche
                self._safe(emit, {"type": "error", "message": f"{type(e).__name__}: {e}"})

        @staticmethod
        def _safe(emit, ev):
            try:
                emit(ev)
            except ClientGone:
                pass

    return Handler


def make_server(app: App, host: str = "127.0.0.1", port: int = 8000) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), make_handler(app))
    server.daemon_threads = True
    return server
