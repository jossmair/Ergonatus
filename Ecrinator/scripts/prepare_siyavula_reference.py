"""Extract original unbranded CC BY schoolbook figures for label/visual review.
Figures with third-party links or attribution are not assumed to inherit book rights.
"""
from pathlib import Path
from zipfile import ZipFile
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO
import posixpath,json,hashlib,re
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'test-output/reference-sources';OUT=ROOT/'assets/library/reference/siyavula';OUT.mkdir(parents=True,exist_ok=True)
items=[];excluded=[];seen=set()
for grade in [7,8,9]:
 z=ZipFile(BASE/f'siyavula-grade{grade}.epub')
 for file in z.namelist():
  if not file.endswith(('.html','.xhtml'))or 'frontmatter'in file:continue
  soup=BeautifulSoup(z.read(file),'html.parser');heading=soup.find(['h1','h2']);chapter=heading.get_text(' ',strip=True)if heading else Path(file).stem
  for figure in soup.find_all('figure'):
   caption=figure.find('figcaption');caption=caption.get_text(' ',strip=True)if caption else ''
   for img in figure.find_all('img',src=True):
    path=posixpath.normpath(posixpath.join(posixpath.dirname(file),img['src']))
    if path not in z.namelist()or not path.lower().endswith('.png'):continue
    if any(w in path.lower() for w in ['cover','logo','icon','qr-code','frontmatter']):continue
    if img.get('alt','').startswith(('http','www.'))or figure.find('a',href=re.compile('^https?://'))or re.search(r'©|copyright|credit:|flickr|wikimedia|commons',caption,re.I):
     excluded.append(dict(path=path,reason='Third-party rights require individual verification',caption=caption));continue
    raw=z.read(path);sha=hashlib.sha256(raw).hexdigest()
    if sha in seen:continue
    seen.add(sha)
    try:im=Image.open(BytesIO(raw))
    except Exception as error:excluded.append(dict(path=path,reason='Image metadata/decode rejected: '+str(error)));continue
    if im.width<180 or im.height<110 or im.width*im.height>12_000_000:continue
    ident='siyavula-'+sha[:16];p=OUT/(ident+'.png');p.write_bytes(raw)
    items.append(dict(id=ident,path=str(p.resolve()),filename=p.name,chapter_en=chapter,caption_en=caption,source_grade=grade,source_html=file,source_image=path,source_url=f'https://www.siyavula.com/downloads/books/science/Gr{grade}_PhysicalSciences_Learner_Eng_CC-BY.epub',author='Siyavula Education',license='CC BY 4.0',license_url='https://creativecommons.org/licenses/by/4.0/',source_sha256=sha,review_status='OCR and visual review required'))
(OUT/'original-candidates.json').write_text(json.dumps(items,ensure_ascii=False,indent=2),encoding='utf-8');(OUT/'third-party-exclusions.json').write_text(json.dumps(excluded,ensure_ascii=False,indent=2),encoding='utf-8')
print('Original PNG candidates',len(items),'third-party exclusions',len(excluded))
