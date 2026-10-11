# Construire le rapport Power BI (environ 2 h)

Le pipeline produit des CSV dans `data/exports/powerbi/` (ou `data/demo/exports/powerbi/` en mode démo).
Le rapport Power BI se branche sur ce dossier : après chaque run du pipeline, un clic sur **Actualiser** suffit.

Enregistre ton fichier sous `powerbi/Observatoire_offre_classee_74.pbix`.

---

## Étape 1 : paramètre et import des données (Power Query)

1. **Accueil > Transformer les données** pour ouvrir l'éditeur Power Query.
2. **Gérer les paramètres > Nouveau paramètre** :
   - Nom : `DossierExports`
   - Type : Texte
   - Valeur : le chemin complet du dossier, **avec la barre oblique finale**, par exemple
     `C:\Users\hamzm\Documents\observatoire-tourisme-74\data\demo\exports\powerbi\`
3. Pour chaque table, **Nouvelle source > Requête vide**, puis **Éditeur avancé** et colle la requête correspondante de
   [`power_query.m`](power_query.m). Renomme la requête avec le nom de la table (`fct_hebergements_classes`, etc.).

> Pourquoi un paramètre ? Pour passer des données de démo aux données réelles, ou déployer le rapport sur une
> autre machine, sans retoucher les requêtes. Pourquoi typer avec la culture `en-US` ? Parce que les CSV utilisent le
> point décimal : avec un Windows en français, sans cette précision, `45.9024` deviendrait `459024`.

4. **Fermer et appliquer**.

## Étape 2 : modèle en étoile (vue Modèle)

Crée les relations suivantes (toutes en **plusieurs à un, filtrage unidirectionnel**) :

| De (côté plusieurs)                     | Vers (côté un)                 |
|-----------------------------------------|--------------------------------|
| `fct_hebergements_classes[code_insee]`  | `dim_commune[code_insee]`      |
| `fct_hebergements_classes[typologie]`   | `dim_typologie[typologie]`     |
| `fct_hebergements_classes[date_classement]` | `dim_date[date_jour]`      |
| `mart_qualite_anomalies[hebergement_id]`| `fct_hebergements_classes[hebergement_id]` |

Ensuite :
- Sélectionne `dim_date`, puis **Outils de table > Marquer comme table de dates**, colonne `date_jour`.
- Dans **Fichier > Options > Données chargées**, décoche « Date/heure automatique » (on a notre propre calendrier).
- Laisse `mart_indicateurs_communes`, `mart_qualite_synthese` et `mart_suivi_ingestions` **sans relation** :
  la première sert au contrôle croisé (étape 5), les deux autres alimentent la page Qualité.
- Masque les colonnes techniques (`hebergement_id`, `fichier_source`, clés étrangères côté faits).
- Catégorie de données : `dim_commune[latitude]` en **Latitude**, `dim_commune[longitude]` en **Longitude**.
- Trie `dim_date[nom_mois]` par la colonne `mois` (**Outils de colonne > Trier par colonne**).

## Étape 3 : mesures DAX

Crée une table vide **Mesures** (**Accueil > Entrer des données**, une colonne, puis supprime-la une fois la
première mesure créée), puis ajoute les mesures de [`mesures_dax.md`](mesures_dax.md).

## Étape 4 : le thème

**Affichage > Thèmes > Parcourir les thèmes**, puis sélectionne [`theme_observatoire.json`](theme_observatoire.json).

## Étape 5 : les pages du rapport

### Page 1 : Vue d'ensemble
- **Segments** : `dim_commune[nom_epci]`, `dim_typologie[famille]`, `fct_hebergements_classes[statut_classement]`.
- **4 cartes** : `[Établissements]`, `[Capacité totale]`, `[Taux de fonction touristique]`, `[% classements à renouveler]`.
- **Carte (bulles)** : latitude et longitude de `dim_commune`, taille = `[Capacité totale]`, info-bulle = `nom_commune`.
  Si le visuel Carte est désactivé : **Options > Sécurité > Utiliser les visuels de carte**.
- **Barres horizontales** : `[Capacité totale]` par `dim_typologie[famille]`.
- **Titre dynamique** : une zone de texte avec une valeur dynamique `[Titre dynamique]`.

### Page 2 : Communes
- **Tableau** : `nom_commune`, `nom_epci`, `[Établissements]`, `[Capacité totale]`, `[Taux de fonction touristique]`,
  `[Part de la capacité départementale]`. Ajoute une mise en forme conditionnelle (barres de données) sur le taux.
- **Nuage de points** : X = `population` (échelle logarithmique), Y = `[Capacité totale]`, détails = `nom_commune`.
  On y lit tout de suite les **communes très touristiques** (beaucoup de lits pour peu d'habitants : stations)
  et les **pôles urbains** (Annecy, Thonon, Annemasse).
- **Top 10** : un histogramme `[Capacité totale]` par commune, filtre de visuel « N premiers = 10 ».

### Page 3 : Classements
- **Courbe** : `[Établissements]` par `dim_date[annee_mois]`, pour voir le rythme des (re)classements.
- **Carte** : `[Classements expirant dans 6 mois]`. C'est l'information directement actionnable pour l'office de
  tourisme, qui peut relancer les hébergeurs avant la perte de leur classement.
- **Tableau** : établissements dont `statut_classement` vaut « Expiré » ou « Expire sous 6 mois », triés par `date_fin_validite`.
- **Histogramme** : `[Établissements]` par `nb_etoiles` (hôtels), avec `[Étoiles moyennes (hôtels)]` en carte.

### Page 4 : Qualité des données
- **Cartes** : `[Taux de fiabilité]`, `[Anomalies bloquantes]`, `[Contrôle de réconciliation]`.
- **Barres** : nombre d'anomalies par `mart_qualite_anomalies[controle]`, légende = `severite`
  (couleurs : Bloquante en rouge, Avertissement en orange, Info en bleu).
- **Tableau** : détail des anomalies (`severite`, `controle`, `nom_commercial`, `commune_source`, `detail`).
- **Courbe** : `mart_suivi_ingestions[nb_lignes]` par `ingere_le`, pour suivre la volumétrie run après run.

> **Ce qu'il faut savoir expliquer en entretien** : la page Qualité montre que l'on ne publie pas un indicateur sans
> savoir dans quelle mesure on peut s'y fier. Le contrôle de réconciliation compare le total calculé en DAX à celui
> calculé par dbt, deux chemins de calcul indépendants qui doivent donner le même chiffre.

## Étape 6 : captures pour le README

Une fois le rapport branché sur les **données réelles**, fais une capture de chaque page
(`Fichier > Exporter > PDF`, ou l'outil Capture d'écran de Windows), enregistre-les dans `docs/` sous
`page1_vue_ensemble.png`, `page2_communes.png`, `page3_classements.png` et `page4_qualite.png`. Le README les affiche.
