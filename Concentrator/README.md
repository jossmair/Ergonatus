# Concentrator 0.3

Clic sur l’Orb : tracez la zone à garder visible sur l’écran contenant le pointeur. Le reste et les autres écrans sont assombris. La zone claire laisse passer les clics vers vos logiciels ; le sombre intercepte le clic et ferme le mode, sans cliquer dans le logiciel derrière. Échap ferme aussi le mode, même lorsque la zone de travail a le focus. Échap ou clic droit annule le tracé ; une zone trop petite est ignorée.

La fenêtre propose un curseur Assombrissement (40 à 100 %, enregistré) et Choisir ma zone. Aucun réglage de largeur/hauteur. Ouvrir la fenêtre depuis le hub, le menu de l’Orb ou son double-clic. Double-clic : fermer le voile et ouvrir les réglages.

Lancer runtime/Concentrator.exe ou le lanceur CMD. Orb 36 px, déplacée avec la pile du hub. Données dans %LOCALAPPDATA%/Ergonatus/concentrator/.

Validation : 118 tests de suite réussis ; quatre tests spécifiques couvrent le tracé depuis l’Orb, le masque natif laissant libre la zone claire, le clic de sortie, Échap global, les petites zones, les écrans disponibles et la persistance du curseur. Les tests ne remplacent pas un essai physique sur toutes les configurations multi-écrans/DPI.
