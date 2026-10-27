"""Compare native PNG and transferred Draw SVG on one problematic vector group."""
from pathlib import Path
import os,subprocess,sys,time,uuid
ROOT=Path(__file__).resolve().parents[1]
PROGRAM=Path('C:/Program Files/LibreOffice/program')
if len(sys.argv)==1:
 from zipfile import ZipFile
 from defusedxml import ElementTree as SafeXML
 from xml.etree import ElementTree as XML
 import copy
 ns={'office':'urn:oasis:names:tc:opendocument:xmlns:office:1.0','draw':'urn:oasis:names:tc:opendocument:xmlns:drawing:1.0'}
 archive=ZipFile(ROOT/'test-output/reference-sources/sesamath/cahier_2025_6e_G1_cours.odt')
 content=SafeXML.fromstring(archive.read('content.xml'));styles=SafeXML.fromstring(archive.read('styles.xml'))
 flat=XML.Element('{'+ns['office']+'}document',{'{'+ns['office']+'}version':'1.3','{'+ns['office']+'}mimetype':'application/vnd.oasis.opendocument.graphics'})
 for parent,name in [(content,'font-face-decls'),(styles,'styles'),(content,'automatic-styles')]:
  found=parent.find('office:'+name,ns)
  if found is not None:flat.append(copy.deepcopy(found))
 body=XML.SubElement(flat,'{'+ns['office']+'}body');drawing=XML.SubElement(body,'{'+ns['office']+'}drawing');page=XML.SubElement(drawing,'{'+ns['draw']+'}page',{'{'+ns['draw']+'}name':'Figure'})
 group=next(e for e in content.findall('.//draw:g',ns) if e.get('{'+ns['draw']+'}name')=='Objet de groupe 20')
 page.append(copy.deepcopy(group));probe=ROOT/'test-output/lo-shape-probe';probe.mkdir(exist_ok=True)
 XML.ElementTree(flat).write(probe/'figure.fodg',encoding='utf-8',xml_declaration=True)
 pipe='ecr_shape_probe_'+uuid.uuid4().hex
 profile=ROOT/'test-output'/pipe
 env=os.environ.copy();env['PYTHONHOME']=str(PROGRAM/'python-core-3.12.14');env['PYTHONPATH']=str(PROGRAM);env['PATH']=str(PROGRAM)+os.pathsep+env['PATH']
 office=subprocess.Popen([str(PROGRAM/'soffice.exe'),'-env:UserInstallation='+profile.as_uri(),'--headless','--norestore','--nodefault','--accept=pipe,name='+pipe+';urp;StarOffice.ServiceManager'],env=env,creationflags=subprocess.CREATE_NO_WINDOW)
 try:
  result=subprocess.run([str(PROGRAM/'python.exe'),str(Path(__file__).resolve()),pipe],env=env,timeout=90,creationflags=subprocess.CREATE_NO_WINDOW)
  sys.exit(result.returncode)
 finally:
  if office.poll()is None:office.terminate()
import uno
sys.stdout=(ROOT/'test-output/lo-shape-probe-worker.log').open('w',encoding='utf-8')
sys.stderr=sys.stdout
from com.sun.star.beans import PropertyValue
from com.sun.star.document.MacroExecMode import NEVER_EXECUTE
from com.sun.star.document.UpdateDocMode import NO_UPDATE
def prop(name,value):
 p=PropertyValue();p.Name=name;p.Value=value;return p
resolver=uno.getComponentContext().ServiceManager.createInstanceWithContext('com.sun.star.bridge.UnoUrlResolver',uno.getComponentContext())
for _ in range(100):
 try:ctx=resolver.resolve('uno:pipe,name='+sys.argv[1]+';urp;StarOffice.ComponentContext');break
 except Exception:time.sleep(.2)
sm=ctx.ServiceManager;desktop=sm.createInstanceWithContext('com.sun.star.frame.Desktop',ctx)
source=ROOT/'test-output/reference-sources/sesamath/cahier_2025_6e_G1_cours.odt'
out=ROOT/'test-output/lo-shape-probe';out.mkdir(exist_ok=True)
doc=desktop.loadComponentFromURL(source.as_uri(),'_blank',0,(prop('Hidden',True),prop('ReadOnly',True),prop('MacroExecutionMode',NEVER_EXECUTE),prop('UpdateDocMode',NO_UPDATE)))
shape=doc.getDrawPage().getByIndex(51)
doc.storeToURL((out/'source-manual.pdf').as_uri(),(prop('FilterName','writer_pdf_Export'),prop('Overwrite',True)))
print('Original size',shape.getSize(),'position',shape.getPosition(),flush=True)
exporter=sm.createInstanceWithContext('com.sun.star.drawing.GraphicExportFilter',ctx)
exporter.setSourceDocument(shape)
print('PNG',exporter.filter((prop('MediaType','image/png'),prop('URL',(out/'native.png').as_uri()),prop('FilterData',(prop('PixelWidth',1000),prop('PixelHeight',1200),prop('Translucent',False))))),flush=True)
try:
 controller=doc.getCurrentController();controller.select(shape);transfer=controller.getTransferable()
 draw=desktop.loadComponentFromURL('private:factory/sdraw','_blank',0,(prop('Hidden',True),))
 draw.getCurrentController().insertTransferable(transfer)
 page=draw.getDrawPages().getByIndex(0)
 print('Draw shapes',page.getCount(),flush=True)
 for i in range(page.getCount()):
  copied=page.getByIndex(i);print('Copied',copied.getSupportedServiceNames(),copied.getPosition(),copied.getSize(),flush=True)
  exporter.setSourceDocument(copied);print('SVG',exporter.filter((prop('MediaType','image/svg+xml'),prop('URL',(out/f'draw-{i}.svg').as_uri()))),flush=True)
 draw.close(True)
except Exception as error:print('DRAW_TRANSFER_ERROR',type(error).__name__,str(error),flush=True)
try:
 template=desktop.loadComponentFromURL('private:factory/sdraw','_blank',0,(prop('Hidden',True),))
 template.storeToURL((out/'template.fodg').as_uri(),(prop('FilterName','OpenDocument Drawing Flat XML'),prop('Overwrite',True)))
 template.close(True)
 from xml.etree import ElementTree as XML
 import copy
 ns={'office':'urn:oasis:names:tc:opendocument:xmlns:office:1.0','draw':'urn:oasis:names:tc:opendocument:xmlns:drawing:1.0'}
 original=XML.parse(out/'figure.fodg').getroot();flat=XML.parse(out/'template.fodg').getroot()
 page=flat.find('.//draw:page',ns)
 for child in list(page):page.remove(child)
 page.append(copy.deepcopy(original.find('.//draw:g',ns)))
 for name in ['font-face-decls','styles','automatic-styles']:
  target=flat.find('office:'+name,ns);extra=original.find('office:'+name,ns)
  if target is not None and extra is not None:
   existing={e.get('{urn:oasis:names:tc:opendocument:xmlns:style:1.0}name')for e in target}
   for child in extra:
    if child.get('{urn:oasis:names:tc:opendocument:xmlns:style:1.0}name') not in existing:target.append(copy.deepcopy(child))
 XML.ElementTree(flat).write(out/'figure-templated.fodg',encoding='utf-8',xml_declaration=True)
 draw=desktop.loadComponentFromURL((out/'figure-templated.fodg').as_uri(),'_blank',0,(prop('Hidden',True),prop('ReadOnly',True),prop('FilterName','OpenDocument Drawing Flat XML'),prop('MacroExecutionMode',NEVER_EXECUTE),prop('UpdateDocMode',NO_UPDATE)))
 page=draw.getDrawPages().getByIndex(0);copied=page.getByIndex(0)
 print('FODG size',copied.getSize(),'position',copied.getPosition(),flush=True)
 point=uno.createUnoStruct('com.sun.star.awt.Point');point.X=1000;point.Y=1000;copied.setPosition(point)
 exporter.setSourceDocument(copied)
 print('FODG SVG',exporter.filter((prop('MediaType','image/svg+xml'),prop('URL',(out/'flat-draw.svg').as_uri()))),flush=True)
 exporter.setSourceDocument(page)
 print('PAGE SVG',exporter.filter((prop('MediaType','image/svg+xml'),prop('URL',(out/'page.svg').as_uri()))),flush=True)
 draw.storeToURL((out/'document.svg').as_uri(),(prop('FilterName','draw_svg_Export'),prop('Overwrite',True)))
 draw.close(True)
except Exception as error:print('FODG_ERROR',type(error).__name__,str(error),flush=True)
doc.close(True);desktop.terminate()
