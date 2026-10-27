# Transcrinator 1.3.17

Le clic droit sur l'orbe ou le hub ouvre le même menu que le clic droit sur l'icône de la zone de notification : ouvrir Transcrinator, afficher le hub, copier le texte conservé et quitter. Les actions et leur disponibilité sont partagées.

À la fin du collage, le hub redevient immédiatement un orbe de 36 × 36, en bas à droite de l'écran où se trouve la souris. La touche de dictée le redéploie en bas au centre. Le traitement est représenté par un trait lumineux continu, animé sans points séparés. Le bord de l'orbe s'efface progressivement dans la transparence, sans plaque circulaire sombre. La vague d'écoute est conservée.

Le collage automatique ne détecte plus les champs et n'interroge plus leur accessibilité. La dictée complète remplace le presse-papiers juste avant un unique Ctrl droit + V, envoyé au focus Windows courant. Aucun contrôle de champ, lecture du résultat ou second collage ne suit cet envoi. Le texte reste disponible pour les applications qui lisent le presse-papiers avec retard.

Le collage utilise Ctrl droit + V, avec des codes de touches adaptés au clavier de la fenêtre active. Ctrl reste maintenu pendant le traitement du raccourci puis est toujours relâché. Si Windows intercepte Ctrl, le logiciel n'envoie pas un V isolé. Aucun second collage automatique n'est tenté après un envoi commencé.

Aucun texte surligné ni champ reconnu par une liste de logiciels n'est requis. Le focus courant de Windows reçoit le collage, sans validation préalable du champ. Même sans éditeur disponible, la dictée complète est copiée et peut être collée ensuite ; aucun message ne demande de sélectionner un champ. Le modèle de reconnaissance et ses réglages restent ceux de la 1.3.13.

Les noms propres et les villes du dictionnaire peuvent maintenant guider directement la reconnaissance, sans réentraînement. Le graphe est préparé une fois et actualisé à l'enregistrement du dictionnaire, sans recharger le modèle. Cette extension s'active automatiquement sur les GPU CUDA de capacité 7.5, dont la NVIDIA T500 vérifiée ici. Les autres configurations gardent leur moteur habituel et les corrections du texte final.

Sur 148 essais synthétiques français répétés trois fois, quatre essais sont améliorés, aucun n'est dégradé ; le temps médian est de 166,95 ms avec le moteur livré précédemment et de 166,79 ms avec le guidage. Ce résultat ne garantit pas la même précision sur toutes les voix réelles. Détails et limites : `docs/validation/context-guidance-1313.json`.

Cette version protège le dictionnaire avec une sauvegarde récupérable et valide les réglages indépendamment. Une panne de capture tente de terminer la transcription de l’audio déjà reçu et conserve le texte récupéré dans le menu de la zone de notification. Une erreur d’écriture des journaux n’arrête plus le service.

Les options ne changent qu’après un enregistrement réussi ; le dictionnaire reste ouvert si l’écriture échoue. L’installateur vérifie une nouvelle copie complète avant de remplacer l’ancienne et restaure la version précédente si l’opération échoue. Une opération interrompue est récupérée au lancement suivant de l’installateur.

Les poids du modèle, la segmentation et les règles de correction du texte restent identiques à 1.3.12. L'extension ajoute un bonus borné aux continuations plausibles des noms, avec des protections pour les mots proches. Si elle ne peut pas se charger, le moteur habituel reprend sur le même GPU.

Votre voix devient du texte, directement dans vos applications Windows.

L’accueil compact mesure **680 × 550** en taille normale, avec un bandeau vocal de 120 pixels de haut. Toutes les options restent visibles à cette taille.

Le choix de la touche s’ouvre dans un panneau arrondi : Maj et Ctrl sont regroupés, et F1 à F12 sont disposées en grille. La sélection est soulignée d’ambre. Les boutons Réduire et Masquer utilisent des icônes tracées avec un survol assorti.

La croix du dictionnaire reprend le même bouton arrondi et le même survol ambré. Elle ferme le dictionnaire sans enregistrer les modifications en cours ; **Enregistrer** les conserve.

Pendant la préparation et la transcription, le hub affiche un trait lumineux continu, parcouru d'une lumière dorée. Cette animation indique une activité en cours, sans pourcentage. La vague à barres reste réservée à l’écoute de la voix.

La mise à jour depuis Transcri conserve le profil existant et remplace le raccourci par **Transcrinator**. Les dossiers internes historiques sont conservés pour retrouver les préférences, les modèles et le verrou d’instance unique.

Chaque dictée insérée se termine par **un espace**, inclus dans le même envoi que le texte. Deux dictées successives restent ainsi séparées sans second collage.

## Utilisation

1. Décompressez entièrement `Transcrinator-1.3.17-Installation.zip`, puis lancez `Installation-Transcrinator-1.3.15/Installer-Transcrinator.exe`. Conservez les quatre fichiers du dossier ensemble. Transcrinator s’ouvre à la fin de l’installation. L’option de démarrage avec Windows reste dans les préférences et son choix existant est conservé.
2. Placez le curseur où vous voulez écrire, si vous souhaitez une insertion automatique.
3. Appuyez sur **Maj gauche**, attendez **Écoute**, puis parlez. Appuyez à nouveau sur **Maj gauche** pour terminer.

Le texte est envoyé **en une fois, au focus Windows courant lorsque la transcription est prête**, avec le contexte des pauses conservé dans une fenêtre audio bornée à 30 secondes. Vous pouvez cliquer dans d’autres champs ou changer d’application pendant la dictée : ces actions ne l’arrêtent plus. La touche choisie termine la capture. Le logiciel ne revient pas dans le premier champ et n'inspecte pas la destination. La dictée reste dans le presse-papiers. Si Windows empêche l'envoi, le texte est aussi conservé en mémoire : clic droit sur l’icône Transcrinator près de l’horloge, puis **Copier le texte non inséré**. Aucun panneau de transcription n’encombre l’accueil. Transcrinator n’affiche aucune notification Windows.

Le microphone Windows par défaut, l’accélération et l’insertion sont choisis automatiquement. Les modèles sont inclus. Aucun compte, aucune clé, aucun téléchargement ni réglage de transcription à effectuer. L’accueil comporte un seul écran. Le hub de **172 × 44**, sans texte, se place en bas au centre de l’écran où se trouve la souris. **Glissez-le à la souris** pour le déplacer ; relâcher après un déplacement n’ouvre pas l’accueil. Dès la fin du collage, il devient un orbe orange de **36 × 36**, en bas à droite de cet écran, avec le même cœur animé et un bord transparent adouci. Il suit la souris lorsqu’elle passe sur un autre écran. **La touche choisie** le remet toujours **au centre en bas** en démarrant la dictée, même si vous l’aviez déplacé. Le microphone reste fermé hors dictée.

Les applications reçoivent un seul collage du texte complet, y compris le Bloc-notes, les champs personnalisés et les barres d'adresse. La dictée reste dans le presse-papiers jusqu'à une nouvelle copie ; les anciennes données texte, HTML, images ou fichiers ne sont jamais rétablies pendant le collage. Une copie effectuée ensuite par l'utilisateur est conservée. Aucun second mode n'est essayé après un envoi commencé. L'absence d'un motif d'accessibilité Edit/TextPattern ou d'un curseur Windows visible ne suffit plus à refuser le focus actif.

Le panneau **Préférences** regroupe quatre cartes : touche de déclenchement, écriture des nombres, unités et démarrage Windows. Les interrupteurs ambrés sont animés et utilisables au clavier. **Touche de déclenchement** propose Maj gauche, Maj droite, Ctrl gauche, Ctrl droit et F1 à F12. Le changement est immédiat et conservé au prochain lancement, sans recharger le modèle. Appuyez puis relâchez la touche seule pour démarrer ou arrêter. Les combinaisons avec une autre touche ne déclenchent pas la dictée ; une touche F choisie seule est réservée à Transcrinator. Maj gauche reste la valeur par défaut ; les instructions et l’infobulle suivent votre choix. Le texte non inséré reste en mémoire jusqu’à sa copie ou à la fermeture de l’application.

## Dictionnaire et nombres

Le bouton **Dictionnaire** permet d’ajouter, modifier et supprimer vos noms propres. Sur un moteur compatible, les noms canoniques des catégories Noms propres et Villes guident aussi le décodeur. Un nom seul rétablit sa casse, ses accents et ses tirets dans le texte final. La colonne facultative **Erreurs habituelles** indique les transcriptions à remplacer : par exemple, nom correct **Josselin**, erreurs **Jocelyn, Joselin**. Ces erreurs ne sont jamais favorisées pendant la reconnaissance. Les remplacements portent sur des termes entiers ; les variantes ambiguës sont refusées. Aucun réentraînement du modèle n'est effectué.

**Ajouter un mot** place la nouvelle ligne en premier et permet de saisir immédiatement son nom. La colonne **Catégorie** propose **Noms propres**, **Villes**, **Produits** et **Mots techniques** ; cliquez sur une catégorie pour la modifier. Les boutons au-dessus du tableau filtrent l’affichage, et **Tous** retrouve l’ensemble. Un ajout dans une catégorie active reçoit cette catégorie. L’ordre et les catégories sont sauvegardés ; enregistrer depuis un filtre conserve aussi les autres mots. Les anciennes entrées sans catégorie affichent **À classer**. Toutes les catégories conservent leurs corrections finales ; seules Noms propres et Villes alimentent le guidage natif, avec priorité aux noms propres et aux ajouts récents dans une liste bornée.

Une seule instance de Transcrinator peut fonctionner pour votre session : un nouveau lancement affiche la fenêtre existante, sans ouvrir un second microphone ni charger un second modèle.

Les termes techniques enregistrés en minuscules conservent la majuscule de début de phrase. Les dictionnaires personnels restent dans les préférences locales et sont conservés lors d’une mise à jour.

L’interrupteur **Nombres en chiffres** règle l’écriture : activé, il écrit `25` ; désactivé, il écrit `vingt-cinq`. L’exemple affiché suit l’état de l’interrupteur. Les noms du dictionnaire, les adresses web et les identifiants numériques ambigus sont préservés. Les articles isolés « un » et « une » restent naturels en mode Chiffres. Ces préférences sont sauvegardées et s’appliquent aux dictées suivantes sans recharger le modèle.

Une dictée finale de moins de **cinq mots** ne reçoit pas de ponctuation de phrase. Les apostrophes, tirets, décimales, heures et adresses web utiles sont conservés.

L’interrupteur **Unités abrégées** écrit les quantités en symboles : `250 grammes` → `250 g`, `cinq kilogrammes` → `5 kg`, `une tonne` → `1 t`, `vingt-cinq litres` → `25 L`, `trois mètres carrés` → `3 m²`. Masses, volumes, distances, surfaces, durées, vitesses et plusieurs unités électriques sont reconnues. La valeur n’est pas changée. La conversion porte sur une unité accompagnée d’une quantité ; les termes isolés restent tels quels. Désactivez l’interrupteur pour conserver les noms d’unités reconnus. Le choix Chiffres/Lettres continue de régler les nombres indépendamment. Cette option est sauvegardée et ne recharge pas le modèle.

L’interrupteur **Démarrage Windows** active ou désactive le lancement réduit à l’ouverture de votre session. La modification concerne uniquement l’entrée Transcrinator de votre compte Windows. Une mise à jour conserve votre choix.

Le hub retrouve sa vague à barres, avec l’amplitude et la sensibilité d’origine, pilotée par le niveau du microphone et plate au silence. À l’activation, le disque émet une impulsion lumineuse ; au réveil, la barre se déploie autour de lui en restant centrée en bas de l’écran. Sa taille finale reste 172 × 44 et son déplacement à la souris reste disponible.

La transcription s’effectue sur votre ordinateur avec **Parakeet Ultra** et Silero VAD. Le microphone est ouvert uniquement pendant la dictée. Les fichiers audio et les transcriptions ne sont pas enregistrés dans les journaux.

## Installation portable

Décompressez entièrement `Transcrinator-1.3.17-Complet.zip`, puis lancez `Transcrinator.exe`. Le mode portable ne crée pas de démarrage Windows automatique. Pour quitter : clic droit sur l’icône Transcrinator dans la zone de notification, puis **Quitter Transcrinator**.

## Configuration

Windows 10/11 x64, microphone autorisé dans les paramètres Windows ; 16 Go de RAM sont conseillés. Le chargement réel détermine si le modèle peut être alloué : aucun seuil calculé à partir de la taille du fichier ne bloque le démarrage. L’accélération compatible est choisie au lancement et le CPU prend le relais si le chargement accéléré échoue. Les pilotes et les droits Windows restent gérés par Windows.

Le collage automatique suit le focus Windows, sans classer les champs. Windows ou l'application peuvent limiter le collage, notamment dans une fenêtre ayant des droits supérieurs ; la dictée reste dans le presse-papiers. La précision dépend de la voix, du bruit et des noms prononcés.

## Développement

Python 3.11+, dépendances figées dans `requirements-lock.txt`. Tests : `python -m pytest -q`. Compilation : `scripts/build.ps1`. Les modèles et runtimes réels doivent être présents et vérifiés avant la création d’une distribution hors ligne. `TRANSCRI_DATA` isole les profils de validation ; `TRANSCRI_BUNDLE` désigne un ensemble de modèles existant.

L’interface orange/ambre conserve ses six images générées et douze petits PNG animés : cœur énergétique, anneaux et plasma. Les images sont incluses et fonctionnent hors ligne. Les coins de la fenêtre sont réellement transparents. Le hub affiche uniquement le cœur et 32 barres pilotées par le volume réel du microphone. La sensibilité visuelle ne modifie pas l’audio envoyé au modèle ; le signal retombe au silence. Les anneaux orbitaux sont décoratifs. Fichiers et prompts : `assets/hud-orange` et `docs/VISUELS-1.3.0.md` dans les sources.

## Licences

Code : MIT. Parakeet Ultra : Moondream et NVIDIA, CC BY 4.0 ; conversion GGUF Q8 par mudler. Silero VAD : MIT. Les attributions et licences des modèles, des runtimes et de CUDA sont incluses dans la distribution.
