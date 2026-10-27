# Calculinator 0.3 — mode Élève

Calculatrice locale à pavé numérique cliquable, calculs exacts et historique. Aucun calcul n’est confié à une IA.

## Utilisation

Le bouton **Mode Élève** affiche un panneau à côté des chiffres. Le choix est enregistré. Désactivez-le pour retrouver la calculatrice compacte habituelle.

- **x, x², y, y²** : insérer les lettres et leurs carrés.
- **√, sin, cos, tan** : insérer une fonction ; le curseur se place entre les parenthèses. Une sélection est entourée par la fonction.
- **a/b** : ouvre la fraction dans l’écran principal, au-dessus des chiffres. Cliquez sur la case du haut ou du bas, puis sur les touches pour remplir le numérateur ou le dénominateur. **Insérer** permet de poursuivre l’expression ; **=** termine directement la fraction et le calcul. Aucun clavier ni fenêtre séparée nécessaire. Les lettres et fonctions utilisent aussi la case sélectionnée. Les fractions imbriquées sont possibles (trois niveaux supplémentaires maximum).
- **π** : insérer pi. Les angles sont **toujours en degrés** ; aucun réglage d’unité à choisir.
- **=** : calculer, développer et simplifier automatiquement. Par exemple `(x+1)²` devient `x² + 2x + 1`, `2x + 3x` devient `5x`, et `1/2 + 1/3` devient `5/6`. Aucun bouton supplémentaire à choisir. Les valeurs trigonométriques remarquables restent exactes.

La multiplication implicite est acceptée : `2x`, `xy`, `(x+1)(x-1)`. La virgule décimale, les puissances avec ^ ou ² et les fractions avec / sont utilisables au clavier. Les conditions de validité des divisions et racines sont conservées dans le message de résultat, y compris après simplification. Ainsi `(x²-1)/(x-1)` devient `x+1` sous la condition `x-1 ≠ 0`. `√(x²)` donne `abs(x)` : x peut être négatif.

Les fractions sont dessinées avec une barre horizontale, le numérateur au-dessus et le dénominateur en dessous. Le champ de saisie affiche cette présentation lorsqu’il n’a pas le focus ; cliquez dans le champ pour éditer au clavier avec la notation /. L’éditeur a/b intégré utilise deux champs centrés, séparés par une barre horizontale. Le résultat garde sa présentation fractionnaire et peut être copié sous une notation texte réutilisable, sans arrondi imposé. Les calculs s’exécutent en arrière-plan ; si la saisie change pendant le traitement, le résultat périmé est écarté.

## Interface et lancement

Fenêtre habituelle de 420 × 650 pixels logiques ; mode Élève élargi à 650 × 650 pour conserver le pavé sans empiler de panneaux supplémentaires. Historique dans une vue séparée, sans compression des touches. Déplacement par la barre supérieure, Alt+F7 pour le clavier, Alt+Espace pour recentrer. Les Orbs conservent leur taille et leur empilement.

Lancer `runtime/Calculinator.exe` ou `Lancer Calculinator.cmd`. Depuis la racine : `python run_satellite.py --app calculinator`.

## Moteur et limites

Arithmétique classique : fractions rationnelles Python. Mode Élève : SymPy 1.14.0 / mpmath 1.3.0. Analyse AST avec liste fermée de nœuds et symboles, sans eval, sympify ou parse_expr sur la saisie. Expressions de 160 caractères maximum, puissances entières de −8 à 8 et limites de complexité. Calcul dans les réels ; pas de résolution d’équations ni de démonstration étape par étape. Un résultat symbolique peut contenir une racine, pi ou une fonction exacte.

Tests : `python -m pytest tests/test_student_math.py tests/test_calculator_workflow.py -q`. Vérification du binaire : `runtime/Calculinator.exe --smoke-test` dans un profil ERGONATUS_DATA isolé. Build : PyInstaller `scripts/satellites.spec` puis `scripts/deploy_satellites.py --app calculinator`, application arrêtée avant déploiement.

Écriture scolaire : les coefficients s’accolent aux lettres (`5x² − 4x + 6`) et x/y s’affichent en Times New Roman italique dans le rendu mathématique et leurs touches. Le signe × reste visible entre deux nombres. Les résultats copiés utilisent également la notation sans × devant x/y.

Saisie améliorée : la ligne active utilise aussi Times New Roman italique, tout en conservant le curseur, la sélection et l’annulation natifs. La fraction se saisit dans un bloc centré compact ; la case active reste mise en évidence pendant l’usage du pavé. Le bouton « En bas / En haut » permet de changer de partie à la souris, sans viser le champ. Insérer poursuit l’expression, égal calcule directement, × annule la fraction.

Interface modernisée : suppression de la phrase explicative sous le panneau Élève. Barre inférieure unique et compacte : Copier, Élève (coché lorsqu’il est actif), Historique / Clavier. Touches sombres adoucies, états survol/pression/focus explicites et égal accentué. Le calcul automatique reste identique.
