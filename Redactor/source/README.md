# REDACTOR 0.4.1

Assistant de rédaction **local** pour Windows 10/11 x64, Python **3.12**, PySide6 et llama-cpp-python. Aucun compte, aucune API payante, aucun serveur distant, aucune télémétrie. Les modèles et les dépendances sont téléchargés uniquement lors de la préparation explicitement demandée.

## Lancer

Double-cliquer sur **Lancer Redactor.cmd**. Le lanceur utilise l’exécutable dans `dist/Redactor-0.4.1` s’il existe, sinon l’environnement `.venv` du dépôt. Ou lancer `.venv\Scripts\python.exe main.py`.

Le modèle par défaut est **Luth-LFM2 700M Q4_K_M**, 468 625 856 octets, choisi après essais locaux de correction et de conservation des noms propres. Il est sous **LFM Open License v1.0**, pas sous Apache ; lire `docs/MODELS.md` et la licence conservée dans `docs/sources`. Les modèles alternatifs sont sélectionnables dans Préférences → Options avancées. Un seul modèle est chargé en RAM.

La fenêtre de **460 × 520** adopte un fond uni sombre et conserve l’orbe rubis de la suite. L’interface fonctionne comme un chat : conversation au centre, demande en bas et options cochables Naturel, Mail et Court en haut ; les autres tons et actions sont dans le menu ⋯. Le contexte récent reste en mémoire et les propositions précédentes restent visibles. Le dernier texte peut être modifié puis copié avec **Copier la réponse**. Les interrupteurs des préférences reprennent ceux de Transcrinator. Les options techniques sont repliées. L’orbe de 36 pixels se place en **quatrième position au-dessus** de Transcrinator, Claviernator et Précisionator. Lorsque le suivi de la suite est activé, glisser Redactor déplace les orbes visibles ensemble et conserve une marge de 16 pixels au-dessus de la barre des tâches. L’option `--link-suite` active ce suivi au lancement ; le menu de l’orbe permet aussi de le retrouver. Une variante violette est disponible dans les options avancées.

## Écrire et corriger

1. Cliquer dans le champ voulu de l’application, puis sur l’orbe rouge, ou utiliser **Ctrl+Alt+R** (modifiable ou désactivable).
2. Saisir une demande, coller un texte, ou cliquer **Récupérer une sélection**. La capture n’altère pas le texte source et n’utilise pas de Ctrl+C.
3. Choisir Rédiger, Répondre, Corriger, Reformuler, Résumer ou Développer dans le sélecteur. Choisir un ton si nécessaire.
4. Cliquer **Générer le texte**. La proposition arrive progressivement ; **Arrêter** interrompt le moteur. Les demandes et propositions restent visibles dans la conversation.
5. Relire et modifier la proposition, puis cliquer **Copier la réponse**. Seule la dernière réponse modifiée est copiée, sans les messages précédents.
6. Dans votre application, coller avec **Ctrl+V** ou le menu **Coller**. Redactor ne choisit pas la destination et ne colle pas automatiquement.

La fermeture de la fenêtre la masque vers l’orbe. **Quitter Redactor** dans le menu de l’orbe ou de la notification libère le modèle, le raccourci et les workers. Un second lancement ouvre l’instance existante.

## Copie et collage volontaire

L’interface propose uniquement **Copier la réponse**. La copie est disponible après la génération et inclut vos modifications. Le contenu du presse-papiers est vérifié après écriture. Les boutons Insérer et Destination ne sont plus exposés. Le service UI Automation reste interne, avec ses tests de sécurité ; il n’est pas déclenché par le bouton Copier. Aucun envoi d’e-mail automatique.

## Installation reproductible et hors ligne

Python 3.12 x64 est requis. Installation avec les wheels du dépôt :

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install.ps1 -Offline -Dev
```

`requirements-lock.txt` conserve les versions réellement utilisées ; `vendor/wheels` contient les distributions Python dont le moteur CPU compilé pour Windows x64. `vendor/SHA256SUMS.txt` permet leur contrôle. Pour réinstaller exactement l’environnement :

```powershell
.venv\Scripts\python.exe -m pip install --no-index --find-links vendor\wheels -r requirements-lock.txt
```

Le script d’installation ne télécharge aucun modèle. Installation explicite de poids supplémentaires :

```powershell
.venv\Scripts\python.exe scripts\download_models.py luth700 --consent
```

Chaque téléchargement est fixé à une révision officielle, reprend un fichier partiel et vérifie taille **et SHA-256** avant utilisation. Les `.part` ne sont jamais chargés. Les modèles se trouvent dans `models`, séparés de l’exécutable. Pour une distribution indépendante du dépôt, copier les modèles retenus dans le dossier `models` à côté de `Redactor.exe`, ou choisir leur chemin absolu dans les préférences.

Après préparation, toutes les fonctions applicatives fonctionnent hors ligne. Le programme affiche une erreur si les poids manquent, sont corrompus, dépassent **2 000 000 000 octets**, ou si la mémoire disponible semble insuffisante. Ce précontrôle mémoire est conservateur, pas une garantie de pic RAM. La version distribuée est testée sur CPU Intel x64 ; les instructions disponibles doivent être vérifiées sur les machines de destination.

## Tests, benchmarks et packaging

```powershell
New-Item -ItemType Directory -Force .test-data
.venv\Scripts\python.exe -m pytest --basetemp .test-data\pytest-local
.venv\Scripts\python.exe scripts\qa_snapshot.py
.venv\Scripts\python.exe scripts\verify_native.py
.venv\Scripts\python.exe -m app.ai.benchmark models\LFM2-700M-Q4_K_M.gguf --tokens 192
powershell -ExecutionPolicy Bypass -File scripts\build.ps1
```

Le test natif ouvre et ferme une **fenêtre de test jetable** ; il n’écrit pas dans les documents utilisateur. Les captures Qt et les rapports sont dans `docs/validation`. Les benchmarks exportent **JSON et CSV**, avec temps de chargement, premier fragment, débit, durée, RSS échantillonné et taille réelle. Les scores de qualité humaine restent vides jusqu’à une relecture suivant la grille documentée. Les vérifications littérales de noms propres ne constituent pas une note objective. Aucune latence fixe n’est promise.

## Architecture

`main.py` gère l’instance unique ; `app/controller.py` relie les signaux Qt. `app/theme.py` centralise couleurs, police, dimensions et styles. `app/ui` contient la fenêtre, l’orbe QPainter et les interrupteurs accessibles. `app/ai` sépare prompts, abstraction AIEngine, backend, métadonnées GGUF, gestion des modèles et benchmarks. `app/windows` isole UI Automation, sélection, raccourci et placement. `app/integration` fournit le pipe local, `app/security` les validations pures.

Deux threads Qt permanents séparent l’inférence et les appels Windows du thread graphique. L’arrêt de génération utilise le callback natif de llama.cpp. Les poids restent en mémoire ; le cache de préfixe est réutilisé quand le backend le permet. **LFM2** nécessite une remise à zéro de son état récurrent entre demandes sur la version verrouillée ; cette adaptation conserve les poids en RAM. Le modèle n’est pas rechargé à chaque génération.

## Fortinator et confidentialité

Redactor reste autonome. `docs/IPC.md` documente le pipe Windows v1, limité au SID et à la session utilisateur, sans port réseau. Le catalogue Fortinator inclut Redactor ; les anciens profils à trois logiciels sont migrés en ajoutant un module non démarré automatiquement. Le centre peut lire l’état et ouvrir Redactor. Les commandes de préparation de texte sont documentées séparément ; **aucune commande IPC ne peut insérer, coller ou envoyer**.

Les préférences seules sont enregistrées dans `%LOCALAPPDATA%\Redactor\settings.json`. Aucun texte, résultat, titre de fenêtre ou contenu de presse-papiers n’est journalisé par Redactor. Le système d’exploitation, les applications cibles et l’historique du presse-papiers Windows peuvent conserver leurs propres données.

## Limites de cette première version

- Les petits modèles peuvent commettre des erreurs, ajouter des formulations ou ignorer des consignes : la relecture est nécessaire.
- Tests réalisés sous Windows 11 sur ce PC ; Windows 10, les différents DPI, lecteurs d’écran et configurations Claviernator nécessitent encore une recette utilisateur sur leurs machines.
- L’insertion sûre est vérifiée sur un champ natif de test, pas sur toutes les applications Windows.
- Qwen3.5 0.8B n’est pas activé avec l’ancien backend verrouillé ; aucune compatibilité n’est inventée.
- Le protocole ne publie pas de capacité d’arrêt distant : quitter se fait localement.
- Exécutable non signé. Aucune installation système ou activation au démarrage n’est effectuée automatiquement.

## Conversation et apparence v2

Les six actions restent dans le sélecteur en haut. Naturel et Professionnel choisissent le ton ; Mail demande une structure de courriel ; Court demande une réponse plus concise. Le mode Corriger préserve le ton et n’applique pas la transformation Mail/Court. La mémoire du modèle est limitée aux derniers échanges (six messages au plus, réduits si le contexte du modèle est plein). Les anciens messages restent affichés mais ne sont pas tous transmis au modèle. Le bouton Nouveau demande confirmation avant d’effacer la conversation. Rien n’est écrit sur disque.

Le fond v2 et l’orbe rubis v2 sont générés à partir des images réelles de Transcrinator et Claviernator. Les PNG sont inclus dans le programme ; aucun service d’image n’est appelé à l’exécution.

## Interface conversationnelle 0.3

Fenêtre compacte de 460 × 520, messages sans encadrés, saisie sans cadre en haut et conversation vide au démarrage. Entrée envoie le message, Maj+Entrée ajoute une ligne. Le menu ⋯ regroupe les actions, les autres tons et les préférences. L’indication de réflexion apparaît uniquement pendant la génération ; l’orbe suit le mode d’animation configuré.

## Saisie et défilement 0.4.1

La saisie et la réponse grandissent avec leur contenu, sans barre de défilement interne. Une seule zone défile pour toute la conversation, y compris la saisie. Entrée envoie, Maj+Entrée ajoute une ligne. Le menu ⋯ permet aussi Envoyer, Arrêter et Nouvelle conversation avec la souris. Le seul bouton d’action visible sous la conversation est Copier la réponse.

La conversation progresse désormais comme un échange SMS : utilisateur à gauche, assistant à droite. Le champ de saisie suit le dernier message et ne reste pas en haut.

## Conversation SMS 0.4

Comme Messages sur Android : vos messages à droite, les réponses à gauche ; saisie ancrée en bas, indépendante du défilement de l’historique. Après chaque réponse, le champ reprend le focus pour continuer. La saisie grandit jusqu’à huit lignes puis reste accessible par défilement, pour garder le bouton d’envoi visible même avec un long brouillon. Les réponses se déploient sans défilement interne. Entrée ou la flèche envoie, Maj+Entrée ajoute une ligne. Copier la réponse copie uniquement la dernière réponse modifiée.
