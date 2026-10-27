"""Export original textbook vector groups through a private LibreOffice instance.
Build tool only. Sources opened read-only, macros and link updates disabled.
"""
import sys,time,json,hashlib
from pathlib import Path
import uno
from com.sun.star.beans import PropertyValue
from com.sun.star.document.MacroExecMode import NEVER_EXECUTE
from com.sun.star.document.UpdateDocMode import NO_UPDATE

def prop(name,value):
 p=PropertyValue();p.Name=name;p.Value=value;return p
pipe=sys.argv[1];source=Path(sys.argv[2]).resolve();out=Path(sys.argv[3]).resolve();out.mkdir(parents=True,exist_ok=True)
local=uno.getComponentContext();resolver=local.ServiceManager.createInstanceWithContext('com.sun.star.bridge.UnoUrlResolver',local)
context=None
for _ in range(150):
 try:context=resolver.resolve('uno:pipe,name='+pipe+';urp;StarOffice.ComponentContext');break
 except Exception:time.sleep(.2)
if context is None:raise RuntimeError('No private LibreOffice connection')
sm=context.ServiceManager;desktop=sm.createInstanceWithContext('com.sun.star.frame.Desktop',context)
entries=json.loads(source.read_text(encoding='utf-8')) if source.suffix=='.json' else [{'filename':source.name,'path':str(source)}]
exclusion_file=source.parent.parent/'sesamath-extraction-exclusions.json'
exclusions=json.loads(exclusion_file.read_text(encoding='utf-8')) if exclusion_file.exists() else {}
seen=set();total=0
for index,entry in enumerate(entries):
 if entry['filename'] in exclusions:
  print('EXCLUDED_SOURCE',entry['filename'],exclusions[entry['filename']],flush=True);continue
 src=Path(entry.get('path',str(source.parent/entry['filename'])));dest=out/src.stem;dest.mkdir(exist_ok=True)
 if (dest/'manifest.json').exists():continue
 doc=None;figures=[]
 try:
  print('OPENING',src.name,flush=True)
  doc=desktop.loadComponentFromURL(src.as_uri(),'_blank',0,(prop('Hidden',True),prop('ReadOnly',True),prop('MacroExecutionMode',NEVER_EXECUTE),prop('UpdateDocMode',NO_UPDATE)))
  if doc is None:raise RuntimeError('Cannot open textbook')
  page=doc.getDrawPage()
  for i in range(page.getCount()):
   shape=page.getByIndex(i)
   if not shape.supportsService('com.sun.star.drawing.GroupShape'):continue
   size=shape.getSize();name=str(shape.getName())
   if size.Width<1200 or size.Height<800 or any(x in name.lower() for x in ['sesamath','logo','carre_droit']):continue
   # Native vector groups only: do not silently inherit third-party photograph rights.
   def vector(s):
    if s.supportsService('com.sun.star.drawing.GraphicObjectShape') or s.supportsService('com.sun.star.drawing.OLE2Shape'):return False
    if s.supportsService('com.sun.star.drawing.GroupShape'):return all(vector(s.getByIndex(k)) for k in range(s.getCount()))
    return True
   if not vector(shape):continue
   file=dest/('figure-'+str(i)+'.svg');exporter=sm.createInstanceWithContext('com.sun.star.drawing.GraphicExportFilter',context)
   try:
    exporter.setSourceDocument(shape);ok=exporter.filter((prop('MediaType','image/svg+xml'),prop('URL',file.as_uri()),prop('Overwrite',True)))
    if not ok or not file.exists():continue
    raw=file.read_bytes();sha=hashlib.sha256(raw).hexdigest()
    if sha in seen:file.unlink();continue
    seen.add(sha)
    figures.append(dict(file=file.name,shape_index=i,shape_name=name,width=size.Width,height=size.Height,sha256=sha))
   except Exception as error:print('FIGURE_ERROR',src.name,i,str(error),flush=True)
  (dest/'manifest.json').write_text(json.dumps(dict(source=entry,figures=figures),ensure_ascii=False,indent=2),encoding='utf-8')
  total+=len(figures);print('EXTRACTED',index+1,len(entries),src.name,len(figures),'TOTAL',total,flush=True)
 except Exception as error:print('SOURCE_ERROR',src.name,str(error),flush=True)
 finally:
  if doc is not None:
   try:doc.close(True)
   except Exception:doc.dispose()
desktop.terminate()
