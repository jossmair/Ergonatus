# Lector 0.5

Lecture locale par voix neuronale, choix Femme ou Homme dans la fenêtre ou le menu de l’icône près de l’horloge. Réglage de vitesse, suivi de phrase, texte/sélection/PDF/DOCX. Ctrl+Alt+F11.

Clic gauche sur l’Orb : un repère de lecture accompagne le pointeur. Sélectionnez normalement un passage dans une application compatible : la lecture démarre au relâchement. Un second clic sur l’Orb arrête la sélection ou la voix. Échap annule la sélection.

Clic droit sur l’Orb : tracez une zone de l’écran. Lector reconnaît son texte et le lit automatiquement avec la voix choisie, sans ouvrir la fenêtre. Échap annule le tracé ; clic gauche sur l’Orb annule la reconnaissance ou arrête la lecture.

Double-clic gauche sur l’Orb : arrêter l’action en cours et ouvrir Lector.

La lecture reste posée, avec un débit légèrement accéléré après le premier réglage trop lent et 0,8 seconde de silence ajouté entre les paragraphes pour les voix naturelles. Les captures sont mises en page automatiquement en arrière-plan : ordre des colonnes, paragraphes et raccord des mots coupés en fin de ligne. Aucun réglage de mise en page n’est nécessaire.

Pendant la préparation avant la parole, un petit sablier vert apparaît au centre de l’écran : sable qui coule et retournement en fin de cycle. Il disparaît au premier segment de parole, à l’arrêt ou en cas d’erreur. Les animations peuvent être désactivées.

Pour ouvrir les réglages et choisir la voix femme/homme : bouton Ouvrir du hub, ou icône Lector près de l’horloge → Ouvrir Lector. Le menu de cette icône propose aussi les voix et Lire une zone de l’écran.

Le clic gauche utilise le texte sélectionné accessible à Windows, sans copier ni modifier le presse-papiers. Le chemin de récupération antérieur est conservé, avec une recherche documentaire complémentaire si nécessaire. Pour les interfaces qui n’exposent pas leur sélection, utilisez le clic droit : la capture OCR fonctionne à partir des pixels visibles, y compris pour les images. La qualité dépend de la lisibilité et des langues OCR Windows installées. Les images temporaires sont effacées après traitement.

Deux modèles locaux, environ 127 Mo au total, sont livrés dans ergoai/voices. La préparation initiale prend quelques secondes en arrière-plan ; aucune donnée n’est envoyée sur Internet. Les voix Windows restent proposées en complément. Le moteur partagé décharge le modèle après trois minutes d’inactivité. Voir docs/LECTOR_VOICE.md pour les mesures et les sources.

Lancer runtime/Lector.exe ou le lanceur CMD de ce dossier. L’Orb flottante mesure 36 px et suit la pile sélectionnée dans le hub.

Données locales dans %LOCALAPPDATA%/Ergonatus/lector/. Voir ../docs/VALIDATION_V2.md pour les tests et limites.

Interface compacte : réglages toujours visibles, voix Femme/Homme et curseur Douce–Rapide. Le bouton de capture et le chargement d’URL sont retirés de la fenêtre ; la capture reste accessible au clic droit sur l’Orb.
