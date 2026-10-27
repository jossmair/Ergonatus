"""Freeze only the manually inspected math cohort, never all extracted groups."""
from pathlib import Path
from PIL import Image
import json,hashlib
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets/library/reference/sesamath'
index=OUT/'editorial-review-index.json'
decisions=json.loads((OUT/'editorial-visual-decisions.json').read_text(encoding='utf-8'))
assert hashlib.sha256(index.read_bytes()).hexdigest()==decisions['index_sha256']
rows=json.loads(index.read_text(encoding='utf-8'))
assert decisions['reviewed_sheets']==list(range(1,17)), 'This release is limited to the first 16 sheets'
accepted=[]
for e in rows[:576]:
 if e['id']in decisions['excluded']:continue
 e=dict(e);image=Image.open(OUT/e['filename']).convert('RGB');image.thumbnail((160,160))
 e.update(monochrome=all(max(p)-min(p)<12 for p in image.getdata()),
  unlabelled=not any(c.isalpha() or c.isdigit()for c in e['figure_labels']),
  review_status='Contrôle visuel individuel des planches 1–16 ; pas de validation enseignante')
 accepted.append(e)
(OUT/'reviewed-collection.json').write_text(json.dumps(accepted,ensure_ascii=False,indent=2),encoding='utf-8')
proof=dict(ids=[e['id']for e in accepted],index_sha256=decisions['index_sha256'],
 contact_sheets=[dict(file=f'assets/library/reference/sesamath/editorial-review-{n}.jpg',
 sha256=hashlib.sha256((OUT/f'editorial-review-{n}.jpg').read_bytes()).hexdigest())for n in range(1,17)],
 exclusions=decisions['excluded'],pending_sheets=list(range(17,62)))
(OUT/'APPROVED-REVIEWED.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2),encoding='utf-8')
print('Reviewed math cohort',len(accepted),'figures;',sum((OUT/e['filename']).stat().st_size for e in accepted),'PNG bytes')
