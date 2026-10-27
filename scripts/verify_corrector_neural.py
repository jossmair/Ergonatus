from pathlib import Path
import sys,os,uuid,json,time,psutil
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
identity='CorrectorNeuralQA-'+uuid.uuid4().hex
os.environ.update(USERDOMAIN=identity,ERGONATUS_DATA=str(root/'.test-data'/identity),ERGONATUS_NO_HOTKEYS='1')
from ergoai.correction import correct
from ergoai.proofreading_client import request
text="Hier, je suis aller au magasin avec mes amis. On a acheter plusieurs chose mais les prix était trop chère. Ensuite, nous somme rentrer chez nous parce qu'il commencer à pleuvoir. J'ai oublier mon sac dans la voiture et personne ne la retrouver. Demain, je retournerais le chercher si j'ai le temp."
start=time.monotonic()
try:
    result=correct(text);normal=result['text'].replace('’',"'")
    for fragment in ["je suis allé","a acheté plusieurs choses","les prix étaient trop chers","nous sommes rentrés","il commençait à pleuvoir","J'ai oublié mon sac","personne ne l'a retrouvé","je retournerai le chercher si j'ai le temps"]:
        assert fragment in normal,(fragment,result['text'])
    report=dict(source=text,result=result,seconds=round(time.monotonic()-start,2))
    (root/'docs/validation/corrector-neural-paragraph.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=True),flush=True)
finally:
    try:
        pid=request(dict(op='status'))['pid'];process=psutil.Process(pid)
        if process.environ().get('USERDOMAIN')==identity:process.terminate()
    except Exception:pass
