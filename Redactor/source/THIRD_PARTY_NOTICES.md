# Composants et licences

Code applicatif Redactor : aucune licence de redistribution générale n’est présumée pour le code utilisateur.

- PySide6-Essentials et shiboken6 : LGPL-3.0 / licences alternatives Qt. Distribution dynamique, fichiers Qt et licences conservés ; respecter les obligations Qt lors d’une redistribution commerciale.
- llama-cpp-python et llama.cpp : MIT. Le moteur local est séparé des poids.
- NumPy : BSD-3-Clause et notices de ses composants ; psutil : BSD-3-Clause.
- pywin32 : licence PSF / notices du projet ; comtypes : MIT.
- Jinja2 et MarkupSafe : BSD-3-Clause ; diskcache : Apache-2.0.
- PyInstaller : GPL avec exception de distribution du bootloader. Non utilisé à l’exécution comme dépendance Python installée.

Les notices détaillées présentes dans les wheels et les distributions installées font foi. La préparation du paquet conserve les métadonnées et licences des bibliothèques distribuées.

## Modèles distincts

- **Luth-LFM2 700M** : Kurakura AI, dérivé de Liquid AI LFM2 ; **LFM Open License v1.0**. La licence originale est dans `docs/sources/Luth-LFM2-700M-GGUF/LICENSE`. Les règles incluent des conditions de redistribution et une condition liée au chiffre d’affaires annuel de 10 millions USD ; ce n’est pas une licence Apache. Les poids ne sont pas intégrés à l’exécutable.
- **Luciole 1B Instruct 1.1** : OpenLLM France / LINAGORA ; Apache-2.0.
- **Qwen2.5 0.5B Instruct** : Qwen ; Apache-2.0.
- **Luth 1.7B Instruct** : Kurakura AI, dérivé de Qwen3 1.7B ; Apache-2.0.

Voir les sources, révisions, tailles et SHA-256 dans `app/ai/model_manager.py` et les reçus de `models`. Conserver les licences et attributions avec toute redistribution des poids.

## Visuels

Le fond rubis est généré par imagegen le 17 octobre 2026 à partir du fond familial Fortinatus, sans modifier l’original. L’orbe rubis v2 et le fond v2 sont générés à partir des références locales de la suite. La variante violette provient de Precisionator/assets/precisionator.png, lui-même dérivé des visuels familiaux MIT. Les interrupteurs et icônes de commandes sont dessinés par Qt. Aucune image n’est téléchargée à l’exécution ; aucun moteur de navigateur n’est requis.
