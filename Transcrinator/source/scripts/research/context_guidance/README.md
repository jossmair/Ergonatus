# Guidage du dictionnaire dans la reconnaissance

Extension additive du moteur Parakeet v0.6.1, ABI 10. Les poids Ultra Q8, le
réseau acoustique et la segmentation audio restent ceux de la distribution.
Un graphe de préfixes privilégie les continuations plausibles de noms propres
et de villes. Il est compilé à l'ouverture du moteur ou quand le vocabulaire
change, jamais à chaque segment audio. Il n'y a ni second passage du modèle,
ni entraînement, ni service distant.

Le bonus est borné à 2 et exige trois caractères de préfixe déjà reconnus.
Les blancs, la ponctuation et les débuts de nouveaux mots ne sont pas remplacés.
Une protection empêche de terminer un nom en supprimant les caractères de la
continuation acoustique. Les tests natifs couvrent aussi les découpages BPE
intermédiaires plus courts, nécessaires aux noms de plusieurs jetons.

Seuls les noms canoniques des catégories `proper_name` et `city` sont proposés
au moteur. Les variantes erronées restent réservées aux corrections du texte
final. La liste native est bornée à 768 variantes, 24 000 octets ; les graphes
trop grands sont refusés et la reconnaissance habituelle continue.

## Reconstruction

Depuis la racine du projet :

```powershell
.venv\Scripts\python.exe scripts/research/context_guidance/prepare.py
```

Les deux archives publiques sont vérifiées par SHA-256 avant extraction. Le
script vérifie aussi les fichiers amont avant d'appliquer `context.patch` et
d'ajouter les trois sources spécifiques. Il refuse d'écraser une expérience
existante. `--target build/autre-source` permet une seconde reconstruction.

Compiler depuis un terminal développeur Windows x64 avec CMake et Ninja.
Définir `VSLANG=1033` avant la configuration pour le suivi des dépendances MSVC.
Utiliser Release, C++17, `/O2 /Ob2 /DNDEBUG /EHsc`, les SDK Windows UM/UCRT et :

```text
PARAKEET_SHARED=ON
PARAKEET_GGML_CUDA=ON
CMAKE_CUDA_ARCHITECTURES=75
GGML_CUDA_NO_VMM=ON
PARAKEET_BUILD_CLI=OFF
PARAKEET_BUILD_SERVER=OFF
PARAKEET_WITH_CED=OFF
PARAKEET_WITH_VOICEDETECT=OFF
GGML_NATIVE=OFF
GGML_AVX2=ON
BUILD_SHARED_LIBS=OFF
```

La validation locale utilise CUDA 12.4, MSVC 19.50 et le SDK 10.0.26100.
Cette combinaison nécessite `-allow-unsupported-compiler` pour nvcc 12.4.
Ne pas modifier les paramètres numériques du moteur ni appliquer des correctifs
GGML supplémentaires sans refaire la comparaison précision/vitesse.

Construire la cible `parakeet`. Avec `PARAKEET_BUILD_TESTS=ON`, construire et
exécuter aussi `test_transcrinator_context`, dont les assertions restent actives
en Release. Certains tests amont utilisent des interfaces POSIX et ne sont pas
directement utilisables sous Windows.

## Distribution et repli

Le binaire retenu est identifié par `validated-runtime.json`. La commande
`python -m scripts.package_turnkey --recognition-runtime chemin/parakeet.dll`
refuse un fichier dont le SHA-256 ne correspond pas au binaire validé.
`scripts/build.ps1 -RecognitionRuntime chemin/parakeet.dll` transmet cette option.

L'extension est placée à côté du runtime CUDA habituel, sous le nom
`parakeet-context-sm75.dll`, et utilise les mêmes dépendances CUDA 12. Elle est
sélectionnée seulement pour le premier périphérique CUDA de capacité 7.5.
Les autres GPU et les moteurs CPU/Vulkan conservent leur runtime livré.
L'échec du contrôle ABI ou du chargement de l'extension rétablit le moteur
habituel sur le même GPU avant d'envisager le repli CPU existant.

Le dictionnaire continue de corriger le texte final sur toutes les configurations.
Les essais de cette version utilisent une voix française synthétique ; leurs
résultats ne garantissent pas la même précision sur toutes les voix réelles.
Les mesures et leurs limites sont consignées dans `docs/validation`.
