# Scanator 0.2

OCR Windows local d’images ou de captures. Texte reconnu modifiable, copie, conservation des lignes et colonnes simples.

Clic gauche sur l'Orb : sélectionner une zone, puis attendre la reconnaissance locale. Le texte est mis en page et copié automatiquement, sans ouvrir la fenêtre. Clic droit : menu sombre avec « Ouvrir Scanator », capture, recentrage et réglages. Échap annule sans remplacer le presse-papiers.

La fenêtre propose des boutons compacts et un aperçu de l'image masqué au départ. Le choix Paragraphes / Lignes d'origine / Colonnes simples est mémorisé. La copie contient du texte et du HTML propre, sans image ni couleur de l'interface. Les logiciels ne prenant pas en charge le HTML reçoivent le texte. Les colonnes simples reposent sur les tabulations reconnues ; la mise en page complète d'une page complexe n'est pas reconstruite.

Lancer runtime/Scanator.exe ou le lanceur CMD de ce dossier. L’Orb flottante mesure 36 px et suit la pile sélectionnée dans le hub.

Données locales dans %LOCALAPPDATA%/Ergonatus/scanator/. Voir ../docs/VALIDATION_V2.md pour les tests et limites.
