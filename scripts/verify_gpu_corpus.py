from pathlib import Path
import sys,time,json,re
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));OUT=ROOT/'output/correction-gpu'
from ergoai.proofreading_service import Proofreader
from ergoai.correction import correct_rules
import threading
host=Proofreader();rows=[]
corpus=["Hier, je suis aller au magasin avec mes amis. On a acheter plusieurs chose mais les prix était trop chère. Ensuite, nous somme rentrer chez nous parce qu'il commencer à pleuvoir. J'ai oublier mon sac dans la voiture et personne ne la retrouver. Demain, je retournerais le chercher si j'ai le temp.","testes pour voir si sa marchent ici la corection gramaticales","Les enfant mange des pomme.","Elle c'est rendu compte qu'il avais oublier ces clé.","Nous avons prit le train à 8h30 et nous somme arriver à Paris à 10h.","Je ne veux pas payer 35 euros demain.","J'ai envoyer les document que tu m'a demander.","Si j'aurais su, je serais pas venu.","La maison que j'ai acheter est très jolie."]
try:
    for source in corpus:
        start=time.perf_counter()
        try:
            prepared=correct_rules(source);neural=host.correct(prepared['text'],threading.Event());assert host.backend.startswith('GPU');result=correct_rules(neural['text']);row=dict(source=source,text=result['text'],remaining=result['remaining'],backend=host.backend,seconds=round(time.perf_counter()-start,3))
        except Exception as e:row=dict(source=source,error=str(e),seconds=round(time.perf_counter()-start,3))
        rows.append(row);print(json.dumps(row,ensure_ascii=True),flush=True);(OUT/'corpus.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
finally:host.unload()
