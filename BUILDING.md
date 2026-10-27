# Construire la suite

Python 3.12 x64 : créer un environnement virtuel puis installer requirements-dev.txt. Les tests Qt requièrent Windows. Les spécifications PyInstaller sont dans scripts/ ; satellites.spec produit les quinze satellites, deploy_satellites.py les place dans leurs dossiers. Le hub démarre via run_ergonatus.py.

Les quatre applications historiques conservent leurs sources et leurs instructions dans <application>/source/. Écrinator et PDFinator sont natifs Rust : installer Rust stable MSVC et le compilateur C++ Windows, puis cargo build --release dans chaque dossier. Cargo télécharge les dépendances du lockfile ; les dossiers target/ et vendor/ ne sont pas publiés.

Les données volumineuses ne sont pas dans Git : récupérer les volumes portables de cette release pour les modèles et runtimes ; les reçus de provenance sont inclus. Dictionnator/data contient le dictionnaire et sa licence dans la distribution.

Les scripts de publication ont des chemins de développement locaux à adapter ; ils ne sont pas des services de mise à jour. Aucune clé n’est incluse. Les binaires ne sont pas signés.
