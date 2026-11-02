"""Chiffres avec leur incertitude (brique 8) -> reports/uncertainty.md

Comparaison A/B observationnelle : abonnés (member) contre occasionnels (casual).
Usage : python scripts/uncertainty.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np  # noqa: E402

from analyst import config, stats  # noqa: E402
from analyst.cleaning import load_clean  # noqa: E402


def fmt(ci, pct=False, unit=""):
    k = 100 if pct else 1
    u = " %" if pct else unit
    return f"{ci['estimate']*k:.2f}{u} [IC 95 % : {ci['low']*k:.2f} ; {ci['high']*k:.2f}]"


def main():
    df = load_clean(config.CLEAN_CSV)
    mem = df[df.member_casual == "member"]
    cas = df[df.member_casual == "casual"]
    lines = ["# Chiffres avec leur incertitude", "",
             f"Données : {len(df)} trajets nettoyés, Jersey City et Hoboken, septembre 2024.", "",
             "## 1. Durée moyenne (minutes)", "",
             f"- abonnés : {fmt(stats.mean_ci(mem.duration_min), unit=' min')} (n = {len(mem)})",
             f"- occasionnels : {fmt(stats.mean_ci(cas.duration_min), unit=' min')} (n = {len(cas)})",
             f"- différence occasionnels - abonnés : "
             f"{fmt(stats.diff_means_ci(cas.duration_min, mem.duration_min), unit=' min')}", "",
             "## 2. Durée médiane (bootstrap, 2000 tirages)", "",
             f"- abonnés : {fmt(stats.bootstrap_ci(mem.duration_min.sample(20000, random_state=0), np.median), unit=' min')} (échantillon de 20 000 trajets)",
             f"- occasionnels : {fmt(stats.bootstrap_ci(cas.duration_min.sample(20000, random_state=0), np.median), unit=' min')} (échantillon de 20 000 trajets)", "",
             "## 3. Part des vélos électriques (IC de Wilson)", ""]
    for name, g in [("abonnés", mem), ("occasionnels", cas)]:
        k = int((g.rideable_type == "electric_bike").sum())
        lines.append(f"- {name} : {fmt(stats.prop_ci(k, len(g)), pct=True)}")
    k1, n1 = int((cas.rideable_type == "electric_bike").sum()), len(cas)
    k2, n2 = int((mem.rideable_type == "electric_bike").sum()), len(mem)
    lines += [f"- différence occasionnels - abonnés : "
              f"{fmt(stats.diff_props_ci(k1, n1, k2, n2), pct=True)} (points)", "",
              "## Ce que ces données ne permettent pas de conclure", "",
              "- **Pas de causalité.** Ce n'est pas un test A/B randomisé : les occasionnels ne "
              "sont pas tirés au sort. Ils roulent plus longtemps peut-être parce que ce sont des "
              "touristes, pas parce qu'ils ne sont pas abonnés. Être abonné ne *raccourcit* pas un trajet.",
              "- **Intervalles trop étroits.** Les intervalles supposent des trajets indépendants. "
              "Or un même abonné fait de nombreux trajets, et le fichier n'a pas d'identifiant "
              "d'usager (bonne chose pour la vie privée) : on ne peut pas corriger cette "
              "dépendance, donc la vraie incertitude est plus grande.",
              "- **Un mois, deux villes.** Septembre 2024 à Jersey City et Hoboken seulement : rien "
              "ne dit que le résultat vaut en hiver ou à Manhattan.",
              "- **Moyenne sensible aux longs trajets.** La moyenne dépend de la règle des 24 h "
              "(journal de nettoyage) ; la médiane est plus robuste.", ""]
    out = config.ROOT / "reports" / "uncertainty.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
