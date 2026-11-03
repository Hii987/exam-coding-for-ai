"""L'interface web : le serveur répond, sans Ollama (faux modèle)."""
import json
import threading
import urllib.request

import pytest

from analyst import guard
from analyst.agent import Agent
from app.server import App, make_server
from tests.test_agent import FakeLLM, say, tool


@pytest.fixture
def server(clean_df, tmp_path):
    results = tmp_path / "results"
    results.mkdir()
    replies = lambda: FakeLLM([tool("result = len(df)"), say("Il y a 4 trajets.")])  # noqa: E731
    app = App(clean_df, replies, results, tmp_path / "expected.json", tmp_path / "log.json",
              traces_dir=None)
    srv = make_server(app, port=0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}", results
    srv.shutdown()


def get(url):
    with urllib.request.urlopen(url, timeout=10) as r:
        return r.read().decode("utf-8")


def post(url, obj):
    req = urllib.request.Request(url, data=json.dumps(obj).encode(), method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


def test_index_and_static(server):
    base, _ = server
    assert "Analyste" in get(base + "/")
    assert "runQuestion" in get(base + "/static/app.js")


def test_static_path_traversal_refused(server):
    base, _ = server
    with pytest.raises(urllib.error.HTTPError):
        get(base + "/static/../server.py")


def test_ask_streams_every_step(server):
    base, _ = server
    raw = get(base + "/api/ask?q=Combien%20de%20trajets%20%3F&mode=system")
    events = [json.loads(line[6:]) for line in raw.splitlines() if line.startswith("data: ")]
    types = [e["type"] for e in events]
    assert types == ["start", "thinking", "llm", "tool", "thinking", "llm", "guard", "done"]
    done = events[-1]
    assert done["status"] == "answered" and done["answer"] == "Il y a 4 trajets."
    assert done["spans"] == [{"start": 7, "end": 8, "text": "4", "kind": "number", "ok": True, "source": 0}]


def test_sandbox_endpoint_blocks(server):
    base, _ = server
    r = post(base + "/api/sandbox", {"code": "import os"})
    assert r["blocked"] and "import" in r["reason"]
    ok = post(base + "/api/sandbox", {"code": "result = len(df)"})
    assert ok["ok"] and ok["output"] == "4"


def test_guard_endpoint(server):
    base, _ = server
    r = post(base + "/api/guard", {"answer": "55 380 trajets, soit 52 %.", "outputs": ["55380"]})
    assert not r["ok"] and r["unsupported"] == ["52"]
    assert [s["ok"] for s in r["spans"]] == [True, False]


def test_bench_endpoint(server):
    base, results = server
    assert json.loads(get(base + "/api/bench")) == {"available": False}
    rows = [{"mode": "system", "run": k, "task": "t01", "expected": 4, "answer": "4", "status": "answered",
             "correct": k != 2, "tokens": 10, "trace": []} for k in (1, 2, 3)]
    for k, r in enumerate(rows, 1):
        (results / f"system_run{k}.jsonl").write_text(json.dumps(r) + "\n")
    b = json.loads(get(base + "/api/bench"))
    assert b["available"] and b["modes"]["system"]["per_run"] == [1, 0, 1]
    t = json.loads(get(base + "/api/bench/trace?mode=system&run=2&task=t01"))
    assert t["correct"] is False


def test_on_event_receives_each_step(clean_df):
    seen = []
    Agent(FakeLLM([tool("result = len(df)"), say("4")]), clean_df).ask("?", on_event=seen.append)
    assert [e["type"] for e in seen] == ["thinking", "llm", "tool", "thinking", "llm", "guard"]


def test_annotate_positions_and_sources():
    spans = guard.annotate("Le 2024-09-13, 5 210 trajets et 99 inventés.",
                           ["2024-09-13    5210"], question="")
    assert [(s["text"], s["ok"], s["source"]) for s in spans] == [
        ("2024-09-13", True, 0), ("5 210", True, 0), ("99", False, None)]
