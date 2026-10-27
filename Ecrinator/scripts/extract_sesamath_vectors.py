"""Use LibreOffice only at build time to preserve Sésamath source drawings exactly."""
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED,ZIP_STORED
from xml.etree import ElementTree as E
from copy import deepcopy
import io,json,re
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'test-output/reference-sources/sesamath-vector';OUT.mkdir(exist_ok=True)
NS={'office':'urn:oasis:names:tc:opendocument:xmlns:office:1.0','draw':'urn:oasis:names:tc:opendocument:xmlns:drawing:1.0','style':'urn:oasis:names:tc:opendocument:xmlns:style:1.0','svg':'urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0','fo':'urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0','text':'urn:oasis:names:tc:opendocument:xmlns:text:1.0','manifest':'urn:oasis:names:tc:opendocument:xmlns:manifest:1.0','xlink':'http://www.w3.org/1999/xlink'}
for k,v in NS.items():E.register_namespace(k,v)
def q(prefix,name):return'{'+NS[prefix]+'}'+name
def document(z,group,path):
 original=E.fromstring(z.read('content.xml'));oldstyles=E.fromstring(z.read('styles.xml'))
 content=E.Element(q('office','document-content'),{q('office','version'):'1.3'})
 fonts=original.find(q('office','font-face-decls'))or oldstyles.find(q('office','font-face-decls'))
 if fonts is not None:content.append(deepcopy(fonts))
 auto=deepcopy(original.find(q('office','automatic-styles')))
 if auto is None:auto=E.Element(q('office','automatic-styles'))
 st=E.SubElement(auto,q('style','style'),{q('style','name'):'ecrDrawingPage',q('style','family'):'drawing-page'});E.SubElement(st,q('style','drawing-page-properties'),{q('draw','fill'):'none'})
 content.append(auto);body=E.SubElement(content,q('office','body'));drawing=E.SubElement(body,q('office','drawing'));page=E.SubElement(drawing,q('draw','page'),{q('draw','name'):'Figure',q('draw','style-name'):'ecrDrawingPage',q('draw','master-page-name'):'ecrMaster'})
 g=deepcopy(group)
 for e in g.iter():
  for key in list(e.attrib):
   if key.startswith('{'+NS['text']+'}')and'anchor'in key:del e.attrib[key]
 page.append(g)
 styles=E.Element(q('office','document-styles'),{q('office','version'):'1.3'})
 for name in ['font-face-decls','styles']:
  element=oldstyles.find(q('office',name))
  if element is not None:styles.append(deepcopy(element))
 sa=E.SubElement(styles,q('office','automatic-styles'));layout=E.SubElement(sa,q('style','page-layout'),{q('style','name'):'ecrPage'})
 E.SubElement(layout,q('style','page-layout-properties'),{q('fo','page-width'):'29.7cm',q('fo','page-height'):'42cm',q('fo','margin-top'):'0cm',q('fo','margin-bottom'):'0cm',q('fo','margin-left'):'0cm',q('fo','margin-right'):'0cm'})
 masters=E.SubElement(styles,q('office','master-styles'));E.SubElement(masters,q('style','master-page'),{q('style','name'):'ecrMaster',q('style','page-layout-name'):'ecrPage'})
 manifest=E.Element(q('manifest','manifest'),{q('manifest','version'):'1.3'})
 for name,mime in [('/','application/vnd.oasis.opendocument.graphics'),('content.xml','text/xml'),('styles.xml','text/xml')]:E.SubElement(manifest,q('manifest','file-entry'),{q('manifest','full-path'):name,q('manifest','media-type'):mime})
 with ZipFile(path,'w',ZIP_DEFLATED)as target:
  target.writestr('mimetype','application/vnd.oasis.opendocument.graphics',compress_type=ZIP_STORED)
  target.writestr('content.xml',E.tostring(content,encoding='utf-8',xml_declaration=True));target.writestr('styles.xml',E.tostring(styles,encoding='utf-8',xml_declaration=True));target.writestr('META-INF/manifest.xml',E.tostring(manifest,encoding='utf-8',xml_declaration=True))
  for name in z.namelist():
   if name.startswith('Pictures/')and not name.endswith('/'):
    target.writestr(name,z.read(name))

def groups(tree):
 parents={c:p for p in tree.iter()for c in p}
 for group in tree.iter(q('draw','g')):
  cursor=parents.get(group)
  while cursor is not None and cursor.tag!=q('draw','g'):cursor=parents.get(cursor)
  if cursor is None:yield group
if __name__=='__main__':
 source=ROOT/'test-output/reference-sources/sesamath-geometry-1.odt'
 with ZipFile(source)as z:
  tree=E.fromstring(z.read('content.xml'));group=next(groups(tree));document(z,group,OUT/'test-figure.odg')
 print(OUT/'test-figure.odg')
