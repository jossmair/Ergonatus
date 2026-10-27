# Traductor — discussion SMS

Fenêtre compacte inspirée de Redactor. En haut : langue de l’utilisateur, langue de sortie et inversion. Écrire un message puis Entrée ou l’icône Envoyer ; Maj+Entrée insère une ligne. Le message source apparaît à gauche, sa traduction à droite.

Chaque bulle contient deux icônes : écouter dans sa propre langue et copier exactement son texte. Un second clic sur l’icône de lecture l’arrête. Changer les langues ne modifie pas les anciennes bulles. Pendant la traduction, Envoyer devient Annuler ; un prochain brouillon reste intact.

Langues proposées : français, anglais, espagnol, allemand, italien, portugais, arabe et ukrainien. Traduction locale avec le modèle Luth-1.7B Q8 déjà partagé avec Corrector et Redactor, sans téléchargement supplémentaire. La qualité varie selon les langues et les passages : les tests réalisés ne constituent pas une garantie d’exactitude universelle.

Lecture entièrement locale pour les huit langues : français, anglais, espagnol, allemand, italien, portugais, arabe et ukrainien. Les modèles Piper et leur moteur sont inclus dans le dossier partagé de la suite. Aucune voix Windows, connexion Internet ou installation de pack supplémentaire n’est nécessaire pendant l’utilisation. L’icône de la bulle lit dans la langue mémorisée de ce message. Une seule voix est chargée à la fois, à la demande ; le premier démarrage ou un changement de langue peut demander quelques secondes. Le second clic arrête la lecture. Le débit est légèrement ralenti ; 400 ms de silence sont envoyées à la sortie audio avant chaque segment pour protéger le début des mots, avec 80 ms en fin de segment.

Les sept modèles supplémentaires occupent 494,1 Mo ; la voix française existante est réutilisée. Notices, révision amont, tailles et empreintes : ergoai/voices/TRADUCTOR_SOURCES.json ; notices françaises : ergoai/voices/SOURCES.json. Gardez le dossier Ergonatus complet. Un fichier supprimé ou endommagé provoque un message de réparation, sans bascule vers un service en ligne.

Clic ou double-clic sur l’Orb : ouvrir la discussion. Clic droit : menu commun, Ouvrir un document (TXT/MD/DOCX/PDF avec texte) et Enregistrer la dernière traduction (TXT/DOCX). Les documents chargés sont placés dans la zone de saisie avant envoi. Ctrl+Alt+F10 ouvre l’application ; raccourci désactivable dans le menu de l’Orb. La croix masque la fenêtre ; Quitter arrête l’application.

Les langues sont enregistrées dans %LOCALAPPDATA%/Ergonatus/traductor. Les messages restent en mémoire pendant la session, sans historique persistant. La traduction est exécutée par ergoai/translation/runtime/ErgoTranslate.exe, avec une file bornée, annulation et déchargement du modèle après 180 secondes d’inactivité. La voix est exécutée par ergoai/translation_voice/runtime/ErgoTranslateVoice.exe, dans un service distinct des voix françaises existantes de Lector et Communicator. Les modèles vocaux restent dans ergoai/voices/. Le modèle de traduction existant reste dans models/ ; ne pas isoler Traductor du dossier de la suite.

## Lancement et compilation

- Utilisateur : runtime/Traductor.exe ou Lancer Traductor.cmd.
- Sources depuis la racine Ergonatus : `python run_satellite.py --app traductor`.
- Moteur : `powershell -File scripts/build_translation.ps1`.
- Voix : exécuter scripts/build_translation_voice.ps1 avec le venv vocal installé ; conserver les modèles et leurs fichiers .onnx.json dans ergoai/voices/.
- Vérification vocale hors ligne : `ergoai/voice/.venv/Scripts/python.exe scripts/verify_traductor_voices.py`.
- Interface : `python -m PyInstaller --noconfirm --distpath .package-satellites --workpath .build-satellites scripts/satellites.spec`, puis `python scripts/deploy_satellites.py --app traductor` après fermeture de Traductor.
- Tests : `python -m pytest tests/test_translator_chat.py -q` ; test compilé réel dans des données temporaires : `Traductor/runtime/Traductor.exe --smoke-test`.

Voir docs/VALIDATION_V2.md pour les résultats et limites des validations.
