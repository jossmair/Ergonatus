# Corrector 0.4 — moteur français de Redactor

Simple clic sur l’Orb : sélectionnez un texte dans une autre application. Le passage est corrigé puis remplace la sélection lorsqu’elle est encore vérifiable. Double-clic : ouvrir la fenêtre. Second clic ou Échap pendant la sélection : annuler. La fenêtre compacte garde Original, Résultat, Corriger, Copier, Restaurer et Annuler.

## Nouveau moteur

Corrector utilise désormais Luth-1.7B-Instruct-Q8_0, déjà présent dans Redactor, chargé avec les modules originaux LlamaEngine, validation GGUF et adaptation de modèle de Redactor. Ces sources de Redactor restent inchangées. Les poids sont copiés localement dans models/ ; aucun téléchargement de modèle ni envoi de texte sur Internet. Fiche officielle : https://huggingface.co/kurakurai/Luth-1.7B-Instruct-GGUF ; empreinte et provenance dans ../ergoai/proofreading/SOURCES.json.

Chaîne : première passe grammaticale spécialisée, correction IA phrase par phrase avec consigne française stricte et trois exemples génériques, vérification grammaticale finale. Génération déterministe (température 0). La première passe préserve notamment les indications de nombre avant que l’IA interprète une phrase ambiguë. Les paragraphes et séparateurs sont conservés. Les propositions trop éloignées, avec ajout de présentation, changement de nombres, négations ou repères temporels sont refusées avant remplacement. Ces contrôles ne garantissent pas toute la sémantique d’un texte arbitraire.

La vérification des temps distingue les contextes explicites au futur avec condition présente des hypothèses à l’imparfait et des demandes polies. Elle utilise la morphologie et le conjugueur du dictionnaire ; aucun remplacement propre au paragraphe de test n’est codé dans le moteur.

Les marques finales manquantes sont ajoutées au-delà de cinq mots. Si la ponctuation existe déjà juste après la sélection, celle ajoutée par l’IA est retirée pour ne pas la doubler. Les points encore détectés comme ambigus sont soulignés et signalés « À vérifier ». Aucun objectif zéro faute universel n’est annoncé comme garanti.

## Service partagé

Moteur local : ergoai/proofreading/runtime/ErgoProofread.exe, protocole AF_PIPE authentifié, demandes bornées, annulation et une file limitée. Une copie du modèle en mémoire, déchargée après trois minutes d’inactivité. Le processus reste disponible pour les appels suivants. Ce service spécialisé garde la compatibilité avec l’ancien service ErgoAI utilisé par Redactor et les autres applications ; il ne remplace pas leur runtime ni leurs réglages. Backend CPU identique à celui testé dans Redactor, interface graphique non bloquée. Le premier traitement d’un long paragraphe peut prendre une vingtaine de secondes sur ce poste.

## Remplacement et restauration

Aucune suppression ou coupe préalable. Champs Windows EDIT : EM_REPLACESEL vérifié, sans presse-papiers. Champs riches exposant une sélection UIA éditable : vérification de la fenêtre, du processus, du contrôle, du document et des positions, puis collage et contrôle du résultat. Les formats de presse-papiers sauvegardables sont restaurés si aucun nouveau contenu n’a été copié entre-temps. Aucun second collage automatique en cas de doute. Texte en lecture seule ou sélection non vérifiable : proposition dans la fenêtre pour copie manuelle.

Restaurer ne réécrit l’original que si le document et le curseur sont encore compatibles avec la transaction. Les textes de travail restent en mémoire, sans historique persistant. Les limites des applications et champs protégés restent applicables.

## Build et validation

Depuis la racine : powershell -File scripts/build_proofreader.ps1, puis PyInstaller scripts/satellites.spec et scripts/deploy_satellites.py --app corrector. Fermer Corrector et le runtime de correction avant d’écraser leurs fichiers lors d’une reconstruction. Le build complet scripts/build_satellites.ps1 inclut le nouveau moteur. Conserver models/Luth-1.7B-Instruct-Q8_0.gguf et son reçu, ainsi que Redactor/source/app/ai/ et les données grammaticales partagées.

--smoke-test vérifie le paragraphe complet signalé par l’utilisateur dans l’application empaquetée. Scripts de tests réels : scripts/verify_corrector_neural.py, verify_corrector_heldout.py et verify_corrector_workflow.py. Rapports et périmètre dans ../docs/VALIDATION_V2.md. Les tests ne constituent pas une garantie de correction exhaustive de tout texte français.
