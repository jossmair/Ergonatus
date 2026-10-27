"""Publish only the reviewed pilot batch; rejected atlas assets stay out of the binary.
The full reference corpus is staged separately and is not claimed as delivered.
"""
from pathlib import Path
from PIL import Image
import json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'assets/library';STAGE=OUT/'reference/sesamath'
archive=json.loads((OUT/'catalog-archive-0.11.json').read_text(encoding='utf-8'))
rejected=set(json.loads((OUT/'reference/REJECTED-0.11.json').read_text(encoding='utf-8'))['excluded_ids'])
base=[]
for e in archive:
 if e['id'] in rejected or e['id'].startswith(('college-region-','college-departement-')):continue
 if e['license']=='Licence Ouverte 2.0':continue
 if e['license']=='MIT':
  assert e['author']=='Écrinator / Ergonatus' and e['source_url'].startswith('urn:ergonatus:ecrinator:illustration:')
  e.update(license='CC BY 4.0',license_url='https://creativecommons.org/licenses/by/4.0/',license_proof_url='urn:ergonatus:ecrinator:original-illustrations-ccby4')
 base.append(e)
# Approval is an explicit immutable ID list, never an index into a growing corpus.
rows=json.loads((STAGE/'candidates.json').read_text(encoding='utf-8'))
approval=json.loads((OUT/'reference/APPROVED-PILOT.json').read_text(encoding='utf-8'))
approved=approval['ids']
assert hashlib.sha256((ROOT/approval['contact_sheet']).read_bytes()).hexdigest()==approval['contact_sheet_sha256']
assert set(approved)<=set(e['id']for e in rows)
for e in rows:
 if e['id'] not in approved:continue
 e=e.copy();target=e['id']+'.png';shutil.copyfile(STAGE/e['filename'],OUT/target);shutil.copyfile(STAGE/(e['id']+'-thumb.png'),OUT/'thumbs'/target)
 source=ROOT/e['vector_source'];dest=OUT/'sources/light'/(e['id']+'.svg');shutil.copyfile(source,dest)
 im=Image.open(OUT/target).convert('RGB');small=im.copy();small.thumbnail((200,200));e.update(filename=target,source_timestamp='Sésamath 6e 2025 · extraction 26/10/2026',changes='Extraction du groupe vectoriel original et rendu PNG. Tracés et annotations conservés. Pas de traduction ni de correction du contenu.',thumbnail_sha256=hashlib.sha256((OUT/'thumbs'/target).read_bytes()).hexdigest(),tags=e['topic']+' '+e['caption'],kind='Figure géométrique',unlabelled=False,monochrome=all(max(p)-min(p)<12 for p in small.getdata()),educational_use='À compléter',review_status='Contrôle visuel Codex · pas de validation enseignante')
 base.append(e)
assert len({e['id']for e in base})==len(base)
assert not any(e['id']in rejected for e in base)
(OUT/'catalog.json').write_text(json.dumps(base,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'licenses/ecrinator-original-illustrations-CC-BY4.txt').write_text('Les illustrations vectorielles originales portant la signature Écrinator / Ergonatus et une source urn:ergonatus:ecrinator:illustration sont proposées sous CC BY 4.0. Crédit : Écrinator / Ergonatus. https://creativecommons.org/licenses/by/4.0/\nLes sources externes conservent leur licence propre. Le code du logiciel conserve ses licences existantes.\n',encoding='utf-8')
shutil.copyfile(ROOT/'test-output/reference-sources/sesamath-license.html',OUT/'licenses/sesamath-license-proof.html')
print('Pilot catalogue:',len(base),'resources,',len(approved),'reviewed textbook figures; rejected atlas removed')
