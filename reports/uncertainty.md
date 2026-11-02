# Chiffres avec leur incertitude

Données : 115308 trajets nettoyés, Jersey City et Hoboken, septembre 2024.

## 1. Durée moyenne (minutes)

- abonnés : 8.12 min [IC 95 % : 8.03 ; 8.21] (n = 85202)
- occasionnels : 14.47 min [IC 95 % : 14.14 ; 14.80] (n = 30106)
- différence occasionnels - abonnés : 6.35 min [IC 95 % : 6.01 ; 6.69]

## 2. Durée médiane (bootstrap, 2000 tirages)

- abonnés : 5.87 min [IC 95 % : 5.80 ; 5.92] (échantillon de 20 000 trajets)
- occasionnels : 8.31 min [IC 95 % : 8.22 ; 8.40] (échantillon de 20 000 trajets)

## 3. Part des vélos électriques (IC de Wilson)

- abonnés : 54.23 % [IC 95 % : 53.90 ; 54.57]
- occasionnels : 68.98 % [IC 95 % : 68.46 ; 69.50]
- différence occasionnels - abonnés : 14.75 % [IC 95 % : 14.13 ; 15.37] (points)

## Ce que ces données ne permettent pas de conclure

- **Pas de causalité.** Ce n'est pas un test A/B randomisé : les occasionnels ne sont pas tirés au sort. Ils roulent plus longtemps peut-être parce que ce sont des touristes, pas parce qu'ils ne sont pas abonnés. Être abonné ne *raccourcit* pas un trajet.
- **Intervalles trop étroits.** Les intervalles supposent des trajets indépendants. Or un même abonné fait de nombreux trajets, et le fichier n'a pas d'identifiant d'usager (bonne chose pour la vie privée) : on ne peut pas corriger cette dépendance, donc la vraie incertitude est plus grande.
- **Un mois, deux villes.** Septembre 2024 à Jersey City et Hoboken seulement : rien ne dit que le résultat vaut en hiver ou à Manhattan.
- **Moyenne sensible aux longs trajets.** La moyenne dépend de la règle des 24 h (journal de nettoyage) ; la médiane est plus robuste.
