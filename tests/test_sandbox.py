"""Brique 3 : on essaie d'enfreindre la règle « le code du modèle ne touche
jamais au système » et on vérifie que c'est bloqué AVANT exécution."""
import pytest

from analyst import sandbox

ATTACKS = [
    "import os\nresult = os.listdir('.')",
    "from subprocess import run\nresult = run(['ls'])",
    "result = open('/etc/passwd').read()",
    "result = __import__('os').system('ls')",
    "result = eval('1+1')",
    "df.to_csv('vol.csv')",
    "result = pd.read_csv('/etc/passwd')",
    "result = df.__class__.__mro__",
    "result = getattr(df, 'to_csv')('x.csv')",
    "result = pd.io.common.os.system('ls')",
    "result = np.lib.npyio.os",
    "result = stats.np.save('x.npy', 1)",
    "result = ().__class__.__bases__[0].__subclasses__()",
    "result = __builtins__.get('_' + '_import__')('os')",
]


@pytest.mark.parametrize("code", ATTACKS)
def test_attacks_are_blocked(code, clean_df, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    res = sandbox.run_code(code, clean_df)
    assert res["ok"] is False and res["blocked"] is True, code
    assert "BLOQUÉ" in res["error"]
    assert list(tmp_path.iterdir()) == []  # aucun fichier écrit


def test_normal_code_runs(clean_df):
    res = sandbox.run_code("result = len(df)", clean_df)
    assert res == {"ok": True, "blocked": False, "output": "4", "stdout": "", "error": None}


def test_stats_available(clean_df):
    res = sandbox.run_code("result = round(stats.mean(df['duration_min']), 2)", clean_df)
    assert res["ok"] and res["output"] == "18.75"


def test_errors_are_returned_not_raised(clean_df):
    res = sandbox.run_code("result = df['colonne_absente']", clean_df)
    assert not res["ok"] and not res["blocked"] and "KeyError" in res["error"]


def test_df_is_a_copy(clean_df):
    sandbox.run_code("df.drop(df.index, inplace=True)\nresult = 0", clean_df)
    assert len(clean_df) == 4


def test_timeout(clean_df):
    res = sandbox.run_code("while True:\n    pass", clean_df, timeout_s=0.5)
    assert not res["ok"] and "délai" in res["error"]


def test_missing_result_hint(clean_df):
    assert "result" in sandbox.run_code("x = 1", clean_df)["output"]


def test_numpy_scalar_shown_as_plain_number(clean_df):
    res = sandbox.run_code("result = df['duration_min'].mean()", clean_df)
    assert res["output"] == "18.75"


# Régression du benchmark v1 : les codes écrits par Qwen, recopiés des traces.
@pytest.mark.parametrize("code,expected", [
    ("len(df)", "4"),
    ("df[df['end_city'] == 'New York'].shape[0]", "1"),
    ("len(df[df['end_city'] == 'New York'])", "1"),
    ("(df[df['end_city'] == 'New York']['ride_id'].count())", "1"),
])
def test_last_expression_is_returned_like_a_notebook(code, expected, clean_df):
    res = sandbox.run_code(code, clean_df)
    assert res["ok"] and res["output"] == expected


def test_explicit_result_wins_over_last_expression(clean_df):
    res = sandbox.run_code("result = 7\nlen(df)", clean_df)
    assert res["output"] == "7"


def test_last_expression_does_not_bypass_the_barrier(clean_df):
    res = sandbox.run_code("open('/etc/passwd').read()", clean_df)
    assert res["blocked"]



# Régression du benchmark v2 (tâche t08), codes recopiés de la trace.
def test_strftime_works_inside_the_sandbox(clean_df):
    code = "df.groupby('started_at').size().sort_values(ascending=False).head(1).index[0].strftime('%Y-%m-%d')"
    res = sandbox.run_code(code, clean_df)
    assert res["ok"] and res["output"] == "'2024-09-01'"


def test_dates_are_shown_as_iso_text(clean_df):
    res = sandbox.run_code("df.groupby(df['started_at'].dt.date).size().idxmax()", clean_df)
    assert res["output"] == "2024-09-02"


def test_internal_import_is_whitelisted():
    with pytest.raises(ImportError):
        sandbox._internal_import("os")
    assert sandbox._internal_import("time").__name__ == "time"
