from pathlib import Path
from zipfile import ZipFile,ZIP_STORED,ZIP_DEFLATED
import json, shutil
r=Path(__file__).resolve().parents[1];out=r/'test-output/odt-diagnostics';out.mkdir(exist_ok=True)
src=r/'test-output/acceptance-v08-final/cours.odt'
with ZipFile(src)as z:
 print(json.dumps([{'name':i.filename,'flag':i.flag_bits,'extra':i.extra.hex(),'offset':i.header_offset,'version':i.extract_version,'method':i.compress_type}for i in z.infolist()[:6]],indent=2))
 for name,strip in [('python-package.odt',False),('without-native.odt',True)]:
  with ZipFile(out/name,'w')as target:
   for info in z.infolist():
    if strip and info.filename.startswith('Ecrinator/'):continue
    data=z.read(info)
    if strip and info.filename=='META-INF/manifest.xml':data=data.replace(b'<manifest:file-entry manifest:full-path="Ecrinator/document.json" manifest:media-type="application/json"/>',b'')
    target.writestr(info.filename,data,compress_type=ZIP_STORED if info.filename=='mimetype'else ZIP_DEFLATED)
shutil.copyfile(r/'test-output/acceptance-v071/cours.odt',out/'baseline-v071.odt')
with ZipFile(out/'minimal.odt','w')as z:
 z.writestr('mimetype','application/vnd.oasis.opendocument.text',compress_type=ZIP_STORED)
 z.writestr('META-INF/manifest.xml','<?xml version="1.0"?><manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" manifest:version="1.3"><manifest:file-entry manifest:full-path="/" manifest:media-type="application/vnd.oasis.opendocument.text"/><manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/></manifest:manifest>')
 z.writestr('content.xml','<?xml version="1.0"?><office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" office:version="1.3"><office:body><office:text><text:p>Bonjour, document de contrôle.</text:p></office:text></office:body></office:document-content>')
