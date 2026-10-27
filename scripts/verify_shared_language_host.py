from pathlib import Path
import sys,os,tempfile,uuid,json,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
identity='FixedLanguage'+uuid.uuid4().hex
os.environ.update(USERDOMAIN=identity,ERGONATUS_DATA=tempfile.mkdtemp(prefix='fixed-language-'))
from ergoai.proofreading_client import request,ensure
from ergoai.translation_client import translate,request as translation_status
from ergoai.correction import correct
rows=[];pid=None
try:
    pid=ensure()['pid'];start=time.monotonic();translation=translate('I need help, please.','en','fr');rows.append(dict(operation='translate',result=translation,seconds=round(time.monotonic()-start,2)))
    start=time.monotonic();correction=correct('Les petite fille joue dans le jardin. Hier, elles sont aller à l’école.');rows.append(dict(operation='correct',result=correction,seconds=round(time.monotonic()-start,2)))
    same=pid==translation_status(dict(op='status'))['pid']==request(dict(op='status'))['pid']
    assert same
    assert 'aide' in translation['text'].casefold()
    assert 'Les petites filles jouent' in correction['text'] and 'elles sont allées' in correction['text']
    report=dict(same_process=same,results=rows);(ROOT/'output/audit/current/shared-language-host.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=True),flush=True)
finally:
    if pid:
        import psutil
        try:
            p=psutil.Process(pid)
            if p.environ().get('USERDOMAIN')==identity:p.terminate()
        except psutil.Error:pass
