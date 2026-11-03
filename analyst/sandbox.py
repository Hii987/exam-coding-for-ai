"""Exécution du code pandas écrit par le modèle, derrière une barrière (brique 3).

La règle est imposée par le code, pas par le prompt : avant d'exécuter, on lit
l'arbre syntaxique (AST) et on refuse tout ce qui pourrait toucher au système
(import, fichiers, réseau, attributs cachés, écriture de fichiers par pandas).
"""
from __future__ import annotations

import ast
import builtins
import io
import re
import threading
from contextlib import redirect_stdout

import numpy as np
import pandas as pd

from analyst import stats

FORBIDDEN_NAMES = {
    "open", "exec", "eval", "compile", "__import__", "globals", "locals", "vars",
    "getattr", "setattr", "delattr", "input", "breakpoint", "exit", "quit",
    "help", "memoryview", "os", "sys", "subprocess", "shutil", "pathlib", "socket",
}
# pandas sait écrire et lire des fichiers : on l'interdit aussi
FORBIDDEN_ATTR = re.compile(r"^(_.*|to_(csv|pickle|parquet|excel|json|sql|hdf|feather|"
                            r"html|latex|markdown|stata|xml|clipboard|orc)|read_\w+|"
                            r"system|popen|load|save|savetxt|loadtxt|fromfile|tofile|"
                            r"os|sys|io|subprocess|builtins|shutil|socket|pathlib|"
                            r"importlib|ctypes|lib|compat|ma|f2py|distutils|testing)$")

SAFE_BUILTINS = {name: getattr(builtins, name) for name in [
    "abs", "all", "any", "bool", "dict", "enumerate", "float", "int", "len", "list",
    "max", "min", "print", "range", "round", "set", "sorted", "str", "sum", "tuple",
    "zip", "isinstance", "map", "filter", "reversed", "Exception", "ValueError",
]}


class Blocked(Exception):
    """Le code a été refusé par la barrière, il n'a pas été exécuté."""


def check_code(code: str) -> None:
    """Lève Blocked si le code enfreint une règle. Ne l'exécute jamais."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise Blocked(f"erreur de syntaxe : {e}") from e
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            raise Blocked("import interdit (pd, np et stats sont déjà disponibles)")
        if isinstance(node, (ast.Global, ast.Nonlocal)):
            raise Blocked("global/nonlocal interdit")
        if isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES:
            raise Blocked(f"nom interdit : {node.id}")
        if isinstance(node, ast.Attribute) and FORBIDDEN_ATTR.match(node.attr):
            raise Blocked(f"attribut interdit : .{node.attr}")
        if isinstance(node, ast.Constant) and isinstance(node.value, str) \
                and node.value.startswith("__"):
            raise Blocked("chaîne '__...' interdite")


def _short(value, max_rows: int = 30) -> str:
    if isinstance(value, np.generic):  # np.float64(48.03) -> 48.03, plus lisible
        value = value.item()
    if isinstance(value, (pd.DataFrame, pd.Series)):
        with pd.option_context("display.max_rows", max_rows, "display.width", 200):
            return str(value.head(max_rows))
    return repr(value)


def last_expression_as_result(code: str):
    """Comme dans un notebook : si le code n'affecte jamais `result` et que sa
    dernière ligne est une expression (`len(df)`), on la transforme en
    `result = len(df)`. Ajouté après le benchmark v1 : Qwen écrivait `len(df)`,
    l'outil ne renvoyait rien, et Qwen inventait un chiffre (voir EVIDENCE.md)."""
    tree = ast.parse(code)
    assigns_result = any(isinstance(n, ast.Name) and n.id == "result" and isinstance(n.ctx, ast.Store)
                         for n in ast.walk(tree))
    if tree.body and isinstance(tree.body[-1], ast.Expr) and not assigns_result:
        last = tree.body[-1]
        tree.body[-1] = ast.Assign(targets=[ast.Name(id="result", ctx=ast.Store())], value=last.value)
        ast.copy_location(tree.body[-1], last)
        ast.fix_missing_locations(tree)
    return tree


def run_code(code: str, df: pd.DataFrame, timeout_s: float = 20.0) -> dict:
    """Exécute `code` avec df, pd, np, stats. La valeur de `result` est renvoyée,
    ou à défaut celle de la dernière ligne si c'est une expression.

    Renvoie {"ok": bool, "output": str, "stdout": str, "error": str|None}.
    """
    try:
        check_code(code)
    except Blocked as e:
        return {"ok": False, "blocked": True, "output": "", "stdout": "",
                "error": f"BLOQUÉ par la barrière : {e}"}

    env = {"__builtins__": SAFE_BUILTINS, "df": df.copy(), "pd": pd, "np": np,
           "stats": stats}
    out = io.StringIO()
    box: dict = {}

    def target():
        try:
            with redirect_stdout(out):
                exec(compile(last_expression_as_result(code), "<run_pandas>", "exec"), env)  # noqa: S102
            box["result"] = env.get("result")
        except Exception as e:  # erreur du code du modèle : on la lui renvoie
            box["error"] = f"{type(e).__name__}: {e}"

    t = threading.Thread(target=target, daemon=True)
    t.start()
    t.join(timeout_s)
    if t.is_alive():
        return {"ok": False, "blocked": False, "output": "", "stdout": out.getvalue(),
                "error": f"délai dépassé ({timeout_s} s)"}
    if "error" in box:
        return {"ok": False, "blocked": False, "output": "", "stdout": out.getvalue()[-2000:],
                "error": box["error"]}
    res = box.get("result")
    output = _short(res) if res is not None else ""
    if not output and not out.getvalue():
        output = "(rien : terminez par une expression, ou assignez la variable `result`)"
    return {"ok": True, "blocked": False, "output": output[:4000],
            "stdout": out.getvalue()[-2000:], "error": None}
