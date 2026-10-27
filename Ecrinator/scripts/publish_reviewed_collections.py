"""Publish visually reviewed collections, keeping unfinished corpora out of builds.

Run offline. Frozen pilot and explicit exclusion decisions make runs repeatable.
"""
from pathlib import Path
from collections import Counter
from PIL import Image
import hashlib, json, shutil

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets/library'
REF = OUT / 'reference'

def read(path):
    return json.loads(path.read_text(encoding='utf-8'))

def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

baseline = REF / 'catalog-pilot-0.11.1.json'
if not baseline.exists():
    current = read(OUT / 'catalog.json')
    assert len(current) == 198, 'Freeze the original pilot before publishing'
    write(baseline, current)
catalog = read(baseline)
coordinate_exclusions = set(read(REF / 'sesamath/COORDINATE-EXCLUSIONS.json')['ids'])
catalog = [e for e in catalog if e['id'] not in coordinate_exclusions]
ids = {e['id'] for e in catalog}
hashes = {e['sha256'] for e in catalog}
decisions = []
reviews = []
publishable = read(REF / 'PUBLISHABLE-IDS.json')

def publish(entry, folder, domain):
    e = dict(entry)
    if e['id'] in ids or e['sha256'] in hashes:
        decisions.append(dict(id=e['id'], reason='Identical ID or image already included'))
        return
    assert e['license'].startswith(('CC BY ', 'CC BY-SA ', 'CC0', 'Public domain'))
    assert all(e.get(k) for k in ['author', 'source_url', 'license_url', 'learning_objective'])
    source = folder / e['filename']
    assert source.name == e['filename'] and sha(source) == e['sha256']
    target = OUT / source.name
    shutil.copyfile(source, target)
    thumb = folder / (e['id'] + '-thumb' + source.suffix)
    shutil.copyfile(thumb, OUT / 'thumbs' / source.name)
    e.update(domain=domain, curriculum_theme=e.get('curriculum_theme') or e['topic'],
             tags=e.get('tags') or ' '.join([e['title'], e['topic'], e['learning_objective']]),
             thumbnail_sha256=sha(thumb),
             review_status='Contrôle visuel des planches et provenance ; pas de validation enseignante')
    for key in ['processed_svg', 'source_svg']:
        if e.get(key):
            shutil.copyfile(folder / e[key], OUT / 'sources/light' / (e['id'] + ('-original.svg' if key == 'source_svg' else '.svg')))
    catalog.append(e)
    ids.add(e['id'])
    hashes.add(e['sha256'])

# Every science review sheet and every literature sheet was inspected, rather
# than extrapolating a few samples to the entire unfinished math corpus.
for collection, count in [('science', 5), ('literature', 10), ('maps', 4)]:
    folder = REF / collection
    for n in range(1, count + 1):
        sheet = folder / f'review-{n}.jpg'
        reviews.append(dict(file=sheet.relative_to(ROOT).as_posix(), sha256=sha(sheet)))

for e in read(REF / 'science/candidates.json'):
    if e['id'] not in publishable['science']:
        continue
    if e['source_name'] in ['mitochondrium-1', 'nucleus']:
        decisions.append(dict(id=e['id'], reason='Detailed organelle outside this introductory college collection'))
        continue
    folder = REF / 'science'
    # Cycle-level indexing avoids asserting that each individual organ is
    # explicitly prescribed in each French class.
    if e['grades'] == ['5e', '4e', '3e']:
        e.update(grades=[], cycle='Cycle 4')
    publish(e, folder, 'science')

for e in read(REF / 'literature/candidates.json'):
    if e['id'] not in publishable['literature']:
        continue
    publish(e, REF / 'literature', 'literature')

excluded_maps = {
    '4448301': 'Specialized Holy Roman Empire map; not a Carolingian Empire map',
    '1820662': 'Generic colonial template with historically misleading kingdom labels',
    '1820672': 'Generic colonial template with historically ambiguous kingdom labels',
    '941299': 'World membership map without a self-contained legend, not European fronts',
    '942048': 'World membership map without a self-contained legend, not European fronts',
    '3882436': 'Cold War world colours without a self-contained legend',
    '19625326': 'Prefer the French-language 118 map for the same Roman historical milestone',
}
exercise_maps = {'6346856', '6346867', '4140215', '1298881'}
for e in read(REF / 'maps/candidates.json'):
    if e['id'] not in publishable['maps']:
        continue
    number = e['id'].removeprefix('reference-map-')
    if number in excluded_maps:
        decisions.append(dict(id=e['id'], reason=excluded_maps[number]))
        continue
    folder = REF / 'maps'
    # Composite the cached Wikimedia raster onto white, preserving transparency
    # correctly. Direct RGBA -> RGB had made transparent seas black.
    image = Image.open(folder / (e['id'] + '-download.bin')).convert('RGBA')
    if max(image.size) > 1800:
        image.thumbnail((1800, 1800))
    white = Image.new('RGBA', image.size, 'white')
    white.alpha_composite(image)
    image = white.convert('RGB')
    # High-quality JPEG avoids shipping multi-megabyte raster relief maps.
    # Source downloads and original SVGs remain untouched for attribution/QA.
    e['filename'] = e['id'] + '.jpg'
    image.save(folder / e['filename'], quality=94, subsampling=0, optimize=True)
    thumb = image.copy(); thumb.thumbnail((300, 190))
    thumb.save(folder / (e['id'] + '-thumb.jpg'), quality=90, optimize=True)
    e['sha256'] = sha(folder / e['filename'])
    if number == '36496257':
        e['title'] = 'La Grande-Grèce · cités et colonies grecques'
    if number in {'1820675', '1820679'}:
        e['language'] = 'en'
    if number in {'6346856', '6346867'}:
        e['language'] = 'zxx'
    if number == '6872417':
        e.update(kind='Document historique', language='la',
                 learning_objective='Comparer une représentation du monde de 1570 avec une carte actuelle.')
    if number == '11433855':
        e.update(title='Europe · fond physique pour localiser les pays de l’UE',
                 educational_use='À compléter', kind='Fond de carte', unlabelled=True)
    if number in exercise_maps:
        e.update(educational_use='À compléter', kind='Carte à annoter',
                 learning_objective='À partir du cours, identifier les espaces représentés et construire une légende explicite.')
    e['changes'] = 'Aperçu Wikimedia composé sur fond blanc et compressé en JPEG de qualité 94, sans sous-échantillonnage chromatique. Source originale conservée séparément.'
    domain = 'science' if 'SVT' in e.get('subjects', []) else 'history' if e.get('category') == 'Histoire' or any(g in e['topic'].lower() for g in ['antiqu', 'guerre', 'empire', 'colon', 'construction européenne', 'révolution']) else 'geography'
    # The selection manifest has explicit topic and school objectives; history
    # subject maps are assigned below from their actual historical titles.
    if number in {'584107','103338061','1540699','36496257','2583635','6346856','6346867','57293890','12047220','153452951','1820675','64563933','1820679','6872417','8849049','1721864','20274155','9798405','2483314','1253616','4140215','51402482'}:
        domain = 'history'
    publish(e, folder, domain)

siyavula_approval = read(REF / 'siyavula/APPROVED.json')
for sheet in siyavula_approval['contact_sheets']:
    assert sha(ROOT / sheet['file']) == sheet['sha256']
    reviews.append(sheet)
siyavula_entries = read(REF / 'siyavula/reviewed-collection.json')
assert [e['id'] for e in siyavula_entries] == siyavula_approval['ids']
for e in siyavula_entries:
    publish(e, REF / 'siyavula', 'science')

math_approval = read(REF / 'sesamath/APPROVED-REVIEWED.json')
for sheet in math_approval['contact_sheets']:
    assert sha(ROOT / sheet['file']) == sheet['sha256']
    reviews.append(sheet)
math_entries = read(REF / 'sesamath/reviewed-collection.json')
assert [e['id'] for e in math_entries] == math_approval['ids']
for e in math_entries:
    assert e['id'] not in coordinate_exclusions
    source = ROOT / e['vector_source']
    shutil.copyfile(source, OUT / 'sources/light' / (e['id'] + '.svg'))
    publish(e, REF / 'sesamath', 'mathematics')

map_additions_approval = read(REF / 'maps-next/APPROVED.json')
assert sha(REF / 'maps-next/metadata.json') == map_additions_approval['metadata_sha256']
map_additions = read(REF / 'maps-next/candidates.json')
assert [e['id'] for e in map_additions] == map_additions_approval['ids']
for e in map_additions:
    assert any(proof['id'] == e['id'] and proof['sha256'] == e['sha256'] for proof in map_additions_approval['images'])
    publish(e, REF / 'maps-next', 'history')

assert len(ids) == len(catalog) == len(hashes)
write(OUT / 'catalog.json', catalog)
write(REF / 'APPROVED-COLLECTIONS.json', dict(
    method='Visual inspection of all listed contact sheets; individual source licences verified. No teacher validation claimed.',
    contact_sheets=reviews, included_ids=[e['id'] for e in catalog if e['id'] not in {b['id'] for b in read(baseline)}],
    excluded=decisions))
report = dict(images=len(catalog), categories=dict(Counter(e['category'] for e in catalog)),
              domains=dict(Counter(e.get('domain', 'starter') for e in catalog)),
              image_bytes=sum((OUT / e['filename']).stat().st_size for e in catalog),
              pending=['Sésamath: sheets 17–61 remain unpublished pending individual review',
                       'Siyavula: 146 visually selected figures; other candidates remain excluded',
                       'Music, technology and languages remain underrepresented'])
write(REF / 'COVERAGE.json', report)
print(json.dumps(report, ensure_ascii=False, indent=2))
