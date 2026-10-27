from pathlib import Path
import sys,os,uuid,json,time,psutil
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
identity='CorrectorHeldoutQA-'+uuid.uuid4().hex
os.environ.update(USERDOMAIN=identity,ERGONATUS_DATA=str(root/'.test-data'/identity))
from ergoai.correction import correct
from ergoai.proofreading_client import request
samples=["Les petite fille joue dans le jardin. Hier, elles sont aller à l'école.","Il ma dit que les réunion était annuler.","Je voudrais un café, s'il vous plaît.","Si j'avais le temps, je viendrais demain.","Demain, je passerais chez Léa si elle est disponible.","Marie a acheté 3 livres pour 24 euros."]
reports=[]
try:
    for source in samples:
        start=time.monotonic();result=correct(source);reports.append(dict(source=source,result=result['text'],remaining=result['remaining'],seconds=round(time.monotonic()-start,2)))
        print(json.dumps(reports[-1],ensure_ascii=True),flush=True)
    normalized=[item['result'].replace('’',"'") for item in reports]
    assert 'Les petites filles jouent' in normalized[0] and 'elles sont allées' in normalized[0]
    assert 'les réunions étaient annulées' in normalized[1]
    assert normalized[2]=="Je voudrais un café, s'il vous plaît."
    assert normalized[3]=="Si j'avais le temps, je viendrais demain."
    assert 'je passerai chez Léa' in normalized[4]
    assert '3 livres' in normalized[5] and '24' in normalized[5]
    (root/'docs/validation/corrector-heldout.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2),encoding='utf-8')
finally:
    try:
        process=psutil.Process(request(dict(op='status'))['pid'])
        if process.environ().get('USERDOMAIN')==identity:process.terminate()
    except Exception:pass
