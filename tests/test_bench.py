import json
from pathlib import Path

from bench.run_bench import score, summarize
from bench.tasks import TASKS, compute_expected


def test_twelve_tasks_with_unique_ids():
    assert len(TASKS) >= 10
    assert len({t["id"] for t in TASKS}) == len(TASKS)


def test_expected_on_small_data(clean_df):
    e = compute_expected(clean_df)
    assert e["t01"] == 4
    assert e["t03"] == 18.75            # (10 + 20 + 40 + 5) / 4
    assert e["t07"] == 1                # D part de Hoboken
    assert e["t12"] == 1                # F finit à New York
    assert e["t08"] == "2024-09-02"


def test_frozen_expected_file_is_complete():
    frozen = json.loads((Path(__file__).resolve().parent.parent / "bench" / "expected.json").read_text())
    assert set(frozen) == {t["id"] for t in TASKS}


def test_score():
    assert score("Il y a 115 308 trajets.", 115308.0, "number")
    assert not score("Il y a 115 000 trajets.", 115308.0, "number")
    assert score("9,78 minutes", 9.7812, "number", 0.01)
    assert score("soit 0,739", 73.89, "number", 0.01)
    assert score("C'est hoboken terminal - river st & hudson pl", "Hoboken Terminal - River St & Hudson Pl", "text")
    assert not score("", 3.0, "number")


def test_summary_mean_and_std():
    rows = [{"mode": "system", "run": r, "task": t["id"], "expected": 1, "status": "answered",
             "correct": (r == 1), "tokens": 100} for r in (1, 2) for t in TASKS]
    s = summarize(rows)
    assert "| system | 2 | 50.0% | 70.7% |" in s


def test_describe_failure_is_readable():
    from bench.show_failures import describe
    row = {"task": "t01", "mode": "system", "run": 2, "status": "refused", "expected": 115308.0,
           "answer": "Je ne peux pas…", "trace": [
               {"step": 0, "type": "llm", "content": "Il y a 115 308 trajets.", "tool_calls": []},
               {"step": 0, "type": "guard", "ok": False, "unsupported": ["115 308"]}]}
    text = describe(row)
    assert "t01" in text and "REFUSE ['115 308']" in text and "Qwen répond : Il y a 115 308" in text


def test_summary_with_a_subset_of_tasks():
    rows = [{"mode": "system", "run": k, "task": "t08", "expected": "2024-09-13", "status": "answered",
             "correct": False, "tokens": 100} for k in (1, 2, 3)]
    s = summarize(rows)
    assert "| t08 | 2024-09-13 | 0/3 |" in s and "| t01 |" not in s
