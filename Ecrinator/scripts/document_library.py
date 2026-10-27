from pathlib import Path
import json
r=Path(__file__).resolve().parents[1]
p=r/'assets/library/catalog.json';items=json.loads(p.read_text(encoding='utf-8'))
corrections={
 'bacterie':('Cellule procaryote · légendes anglaises','bactérie cellule procaryote anglais'),
 'adn':('ADN · légendes anglaises','adn génétique anglais'),
 'atome':('Hélium · densité électronique','atome hélium électron noyau modèle quantique'),
 'lentille':('Lentille convergente · légendes anglaises','optique lentille convergente rayons anglais'),
 'etats-matiere':('États de la matière · anglais','solide liquide gaz états matière anglais'),
}
for e in items:
 if e['id'] in corrections:e['title'],e['tags']=corrections[e['id']]
p.write_text(json.dumps(items,ensure_ascii=False,indent=2),encoding='utf-8')
text='# Bibliothèque scolaire Écrinator\n\n19 images disponibles hors ligne, classées en Cartes, SVT et Physique-chimie.\nLes documents sources sont fournis sous les licences indiquées pour chaque fichier, indépendamment de la licence du logiciel.\nLes fichiers PNG/JPEG sont les vignettes fournies par Wikimedia Commons. Aucun schéma scientifique n’a été généré par IA.\nCertaines légendes sont en anglais : elles sont signalées dans les titres. Les cartes ont une date et ne constituent pas une source géopolitique actualisée.\nLe contenu pédagogique doit être choisi par l’enseignant selon le cours.\n\n'
for e in items:
 text+=f"## {e['title']}\n\n- Fichier : `{e['filename']}`\n- Auteur/crédit : {e['author']}\n- Source : {e['source_url']}\n- Licence : {e['license']} — {e['license_url'] or e['source_url']}\n- Version source : {e['source_timestamp']}\n- Téléchargement : {e['retrieved']}\n- Traitement : {e['changes']}\n- SHA-256 : `{e['sha256']}`\n\n"
(r/'assets/library/ATTRIBUTION.md').write_text(text,encoding='utf-8')
p=r/'assets/ATTRIBUTION.md';s=p.read_text(encoding='utf-8')
if 'Bibliothèque scolaire — 0.8.0' not in s:s+='\n\n## Bibliothèque scolaire — 0.8.0\n\n19 fichiers téléchargés depuis Wikimedia Commons, sous domaine public, CC0, CC BY ou CC BY-SA selon le fichier. Les crédits, licences, liens sources, versions et empreintes de chaque image sont consignés dans library/ATTRIBUTION.md et library/catalog.json. Les métadonnées source intégrales sont dans les fichiers library/*.source.json. Ces ressources tierces conservent leurs licences propres.\n'
p.write_text(s,encoding='utf-8')
