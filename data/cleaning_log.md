# Journal de nettoyage

| étape | avant | après | retirées | valeurs modifiées | raison | source |
|---|---|---|---|---|---|---|
| doublons ride_id | 115558 | 115558 | 0 |  | un trajet = une ligne | décision de l'analyste |
| dates illisibles | 115558 | 115558 | 0 | 231116 | started_at/ended_at convertis en datetime ; lignes non convertibles retirées | décision de l'analyste |
| durée <= 0 | 115558 | 115558 | 0 |  | fin avant le début : erreur d'horodatage | décision de l'analyste |
| durée < 60 s | 115558 | 115558 | 0 |  | Les trajets de moins de 60 secondes ne sont pas de vrais trajets (faux départs, re-dépôt du vélo) ; les trajets du personnel et des stations de test non plus. | Citi Bike, page 'System Data' (https://citibikenyc.com/system-data) |
| durée > 24 h | 115558 | 115531 | 27 |  | Un vélo non rendu au bout de 24 heures est considéré comme perdu ou volé : un 'trajet' de plus de 24 h n'est pas un trajet. | Citi Bike, contrat de location / FAQ tarifs (https://citibikenyc.com/pricing) - à vérifier et citer précisément |
| id station d'arrivée reconstitué | 115531 | 115531 | 0 | 30 | id manquant mais nom présent : id retrouvé grâce au nom (même nom = même station) | décision de l'analyste |
| station d'arrivée manquante | 115531 | 115308 | 223 |  | vélo non rendu en station (coordonnées arrondies à 0,01°) : trajet incomplet | décision de l'analyste |
| ville déduite de l'id de station | 115308 | 115308 | 0 | 230616 | Le préfixe de l'identifiant de station donne la ville : HB = Hoboken, JC = Jersey City ; un identifiant numérique (ex. 6432.11) est une station de New York. Id d'une autre forme : ligne retirée. | Carte des stations Citi Bike (stations HBxxx toutes à Hoboken) ; vérifié sur les coordonnées : les ids numériques sont à Manhattan (longitude > -74.02, ex. 'E 40 St & Park Ave') |
