# Planinator — agenda simple

## Ajouter une note

- Cliquer **+** sur un jour, ou dans son espace vide.
- Pour plusieurs jours, **glisser du premier au dernier jour**, puis relâcher : la fiche s’ouvre directement pour toute la période, jours intermédiaires inclus. Aucun bouton de sélection à activer.
- Un clic sur le numéro d’un jour affiche sa vue détaillée. Le mois garde seulement ses 4, 5 ou 6 semaines nécessaires, sans défilement.

## Mode Élève

Activer **Mode Élève**. Une nouvelle entrée ouvre directement une fiche courte : **matière**, **texte**, **Enregistrer**. Chaque matière a sa couleur automatique ; **Rendez-vous** est proposé dans la même liste. Aucun titre séparé, type, horaire ou choix de couleur à régler dans cette fiche.

Les matières du collège et les options déjà proposées sont conservées. Les anciens titres des entrées scolaires sont repris dans le texte lorsqu’ils contiennent une information distincte. Les notes existantes restent présentes. Une entrée scolaire ouverte depuis le mode habituel conserve sa fiche simple ; un rendez-vous habituel ouvert en mode Élève est proposé sous Rendez-vous, avec son texte conservé.

- Dans une note : sélectionner du texte, puis l’icône **surligneur** ou **S barré** sous le texte. Réappuyer sur l’icône retire la marque de la sélection.
- Sur les cartes détaillées (Jour, Semaine, widget) : les mêmes icônes mettent en évidence ou barrent **l’élément entier**. En vue Mois, cliquer la carte pour ouvrir la fiche et ses outils.
- Les marques du texte sont enregistrées avec la note. Barrer une carte ne supprime pas son contenu.

Le mode habituel conserve sa fiche de rendez-vous détaillée et son choix de couleur. Changer de mode ne supprime aucune entrée. Les couleurs scolaires affichées sont toujours celles des matières, y compris pour les anciennes entrées qui avaient une couleur manuelle.

## Orb et widget

Un clic sur l’Orb affiche/masque Aujourd’hui et Demain ; double-clic ou menu Ouvrir affiche l’agenda. Le widget ajuste sa hauteur au contenu, jusqu’à la taille disponible de l’écran ; son fond se règle avec le curseur Fond. Glisser MON AGENDA pour le déplacer. Échap ou × masque le widget.

## Données, lancement et vérification

Données locales : `%LOCALAPPDATA%/Ergonatus/planinator/records.sqlite3`. Les suppressions sont logiques ; Annuler la suppression restaure la dernière suppression de la session. Aucune synchronisation Google ou scolaire, import d’emploi du temps, récurrence ou invitation.

Lancer `runtime/Planinator.exe` ou `Lancer Planinator.cmd` ; depuis la racine : `python run_satellite.py --app planinator`.

Tests : `python -m pytest tests/test_planinator.py -q`. Captures isolées : `python scripts/validate_planinator_school.py`. Le smoke-test écrit uniquement dans un **nouveau dossier ERGONATUS_DATA** défini pour la validation.

Compilation depuis la racine :

```powershell
$env:ERGONATUS_BUILD_APP = 'planinator'
../Redactor/.venv/Scripts/python.exe -m PyInstaller --noconfirm --distpath .package-satellites --workpath .build-satellites scripts/satellites.spec
../Redactor/.venv/Scripts/python.exe run_satellite.py --app planinator --quit-running
# Attendre l’arrêt du processus avant le déploiement.
../Redactor/.venv/Scripts/python.exe scripts/deploy_satellites.py --app planinator
```

Les fiches de note/modification restent au premier plan jusqu’à leur fermeture. La liste des matières possède un fond sombre, des lignes espacées et une pastille de couleur par matière ; elle reste au-dessus de la fiche pendant le choix.
