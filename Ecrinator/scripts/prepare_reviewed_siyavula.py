"""Prepare the explicit visual selection; no OCR-only automatic acceptance.

Indices refer to one frozen review index, guarded by its SHA-256. The output
records stable image IDs and all inspected contact sheets for later review.
"""
from pathlib import Path
from zipfile import ZipFile
from PIL import Image
import hashlib, json

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets/library/reference/siyavula'
index = OUT / 'unlabelled-review-index.json'
EXPECTED = 'a520fd12a5554c69cc4ae35495c5c0ffaf5d707ea437b689b40c0555fd23f326'
assert hashlib.sha256(index.read_bytes()).hexdigest() == EXPECTED, 'Review order changed: reselect by stable ID'
rows = json.loads(index.read_text(encoding='utf-8'))
for grade in [7, 8, 9]:
 archive = ZipFile(ROOT / f'test-output/reference-sources/siyavula-grade{grade}.epub')
 frontmatter = [name for name in archive.namelist() if 'frontmatter' in name and name.endswith(('.html','.xhtml'))]
 assert len(frontmatter) == 1
 proof = archive.read(frontmatter[0]).decode('utf-8')
 assert 'creativecommons.org/licenses/by/4.0' in proof
 (ROOT / f'assets/library/licenses/siyavula-grade{grade}-frontmatter.html').write_text(proof, encoding='utf-8')
topics = {
 'Acids, bases and neutral substances': ('Physique-chimie','Acidité et indicateurs','Comparer des milieux à l’aide d’un indicateur coloré.'),
 'Acids, bases and the pH value': ('Physique-chimie','Acidité et indicateurs','Comparer les couleurs prises par un indicateur de pH.'),
 'Electric cells as energy systems': ('Physique-chimie','Piles et circuits','Identifier les composants d’une pile ou d’un circuit simple.'),
 'Energy and the national electricity grid': ('Physique-chimie','Énergie et conversions','Identifier une conversion d’énergie dans un dispositif simple.'),
 'Atoms': ('Physique-chimie','Atomes et molécules','Distinguer atome, molécule et assemblage de particules.'),
 'Cells as the basic units of life': ('SVT','Cellules','Identifier les structures représentées et compléter les légendes à partir du cours.'),
 'Chemical reactions': ('Physique-chimie','Transformations chimiques','Identifier les réactifs et les produits dans un modèle de transformation chimique.'),
 'Circulatory and respiratory systems': ('SVT','Respiration et circulation','Repérer les organes et mettre en relation leur organisation avec leur fonction.'),
 'Compounds': ('Physique-chimie','Atomes et molécules','Interpréter une représentation moléculaire et distinguer mélange et corps pur.'),
 'Digestive system': ('SVT','Alimentation et digestion','Repérer les organes digestifs et relier les aliments aux besoins de l’organisme.'),
 'Energy transfer in electrical systems': ('Physique-chimie','Circuits électriques','Passer du montage au schéma et repérer les transferts d’énergie.'),
 'Forces': ('Physique-chimie','Forces et interactions','Identifier une action mécanique, son effet et sa représentation.'),
 'Heat: Energy transfer': ('Physique-chimie','Transferts thermiques','Décrire une expérience et comparer les transferts thermiques.'),
 'Historical development of astronomy': ('Physique-chimie','Observer le ciel','Reconnaître une représentation de constellation et la distinguer des objets réels.'),
 'Human reproduction': ('SVT','Reproduction humaine et puberté','Repérer les transformations de la puberté et les organes de la reproduction.'),
 'Interactions and interdependence within the environment': ('SVT','Étudier un milieu','Décrire une méthode d’échantillonnage d’un milieu.'),
 'Looking into space': ('Physique-chimie','Lumière et vision','Suivre le trajet de la lumière dans un modèle optique.'),
 'Particle model of matter': ('Physique-chimie','États de la matière','Interpréter un modèle particulaire et le relier à une observation.'),
 'Potential and kinetic energy': ('Physique-chimie','Énergie et mouvement','Identifier les formes et les transferts d’énergie dans une situation simple.'),
 'Properties of materials': ('Physique-chimie','Propriétés des matériaux','Proposer des observations permettant de comparer des matériaux.'),
 'Reactions of acids with metals': ('Physique-chimie','Transformations chimiques','Décrire un montage de reconnaissance ou de recueil d’un gaz.'),
 'Reactions of metals with oxygen': ('Physique-chimie','Transformations chimiques','Relier le montage expérimental aux observations.'),
 'Relationship of the Sun to the Earth': ('SVT','Ressources fossiles','Remettre en ordre les représentations et expliquer la formation d’une ressource fossile.'),
 'Resistance': ('Physique-chimie','Circuits et conducteurs ohmiques','Repérer les éléments d’un circuit et comparer des conducteurs.'),
 'Safety with electricity': ('Physique-chimie','Circuits et sécurité électrique','Repérer les branches d’un circuit ou analyser une situation à risque.'),
 'Separating mixtures': ('Physique-chimie','Séparer les mélanges','Associer une technique de séparation à ses observations et au mélange étudié.'),
 'Series and parallel circuits': ('Physique-chimie','Circuits en série et en dérivation','Repérer les branches et placer les appareils de mesure dans un circuit.'),
 'Sexual reproduction': ('SVT','Reproduction et dispersion des graines','Relier les structures représentées à la reproduction et à la dispersion.'),
 'Static electricity': ('Physique-chimie','Charges électriques','Interpréter une représentation des charges électriques.'),
 'The Periodic Table of Elements': ('Physique-chimie','Éléments chimiques','Compléter les cases avec les symboles étudiés à partir d’un tableau de référence.'),
 'The lithosphere': ('SVT','Structure de la Terre','Identifier les couches représentées et compléter les légendes.'),
 'Variation': ('SVT','Diversité du vivant','Comparer des caractères observables sans en déduire automatiquement leur hérédité.'),
 'Visible light': ('Physique-chimie','Lumière et vision','Suivre des rayons lumineux et comparer réflexion, diffusion et réfraction.'),
}
accepted = []
for line in (OUT / 'selection-fr.tsv').read_text(encoding='utf-8').splitlines():
 if not line.strip(): continue
 number, title = line.split('\t', 1)
 e = dict(rows[int(number)])
 category, topic, objective = topics[e['chapter_en']]
 if int(number) in [143,144,145,146,149,357]:
  category,topic,objective='SVT','Reproduction humaine et puberté','Repérer les organes, décrire la puberté et distinguer fécondation et développement.'
 if int(number) == 196:
  category,topic,objective='SVT','Relations alimentaires','Identifier les organismes et interpréter le sens des flèches d’une chaîne alimentaire.'
 raw=OUT/e['filename']; original=raw.read_bytes()
 assert hashlib.sha256(original).hexdigest()==e['source_sha256']
 image=Image.open(raw); image.load()
 # Preserve original pixels; remove excessive ancillary PNG metadata only.
 target=OUT/(e['id']+'-compact.png')
 image.save(target,optimize=True)
 thumb=image.copy();thumb.thumbnail((300,190));thumb.save(OUT/(e['id']+'-thumb.png'),optimize=True)
 sample=image.convert('RGB');sample.thumbnail((150,150))
 mono=all(max(p)-min(p)<12 for p in sample.getdata())
 e.update(title=title,category=category,subjects=[category],topic=topic,curriculum_theme=topic,
  learning_objective=objective,grades=[],cycle='Cycle 4',domain='science',
  kind='Schéma à étudier',educational_use='À étudier',language='zxx',unlabelled=True,
  monochrome=mono,width=image.width,height=image.height,filename=target.name,
  sha256=hashlib.sha256(target.read_bytes()).hexdigest(),tags=' '.join([title,topic,objective]),
  caption='Illustration issue du manuel scolaire libre Siyavula. Titre français de classement ; dessin original conservé.',
  changes='Titre et classement français ; pixels conservés, métadonnées PNG allégées. Pas de traduction de texte imprimé.',
  license_proof_url='https://www.siyavula.com/read',source_timestamp='EPUB scolaire CC BY 4.0 ; empreinte du fichier image source conservée',
  review_status='Sélection visuelle explicite sur les 18 planches ; pas de validation enseignante')
 if int(number) in [23,24,28,43,44,45,60,65,145,343,372,379]:
  e.update(kind='Schéma à légender',educational_use='À compléter')
 accepted.append(e)
result=OUT/'reviewed-collection.json';result.write_text(json.dumps(accepted,ensure_ascii=False,indent=2),encoding='utf-8')
proof=dict(index_sha256=EXPECTED,ids=[e['id']for e in accepted],contact_sheets=[dict(file=f'assets/library/reference/siyavula/review-{n}.jpg',sha256=hashlib.sha256((OUT/f'review-{n}.jpg').read_bytes()).hexdigest())for n in range(1,19)],method='Individual visual selection, no OCR-only acceptance; French titles; grade 7–9 is not equated with a French class.')
(OUT/'APPROVED.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2),encoding='utf-8')
print(len(accepted),'explicitly selected figures; no publication of other candidates')
