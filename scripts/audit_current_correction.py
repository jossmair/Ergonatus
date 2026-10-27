from pathlib import Path
import os,sys,uuid,json,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
os.environ.update(USERDOMAIN='CurrentCorrection'+uuid.uuid4().hex,ERGONATUS_DATA=str(ROOT/'output/audit/current/private-data'))
from ergoai.correction import correct
rows=[]
for text in ["Les petite fille joue dans le jardin. Hier, elles sont aller à l'école.","Je voudrais un café, s'il vous plaît."]:
    start=time.monotonic()
    try:row=dict(source=text,result=correct(text))
    except Exception as error:row=dict(source=text,error=str(error))
    row['seconds']=round(time.monotonic()-start,2);rows.append(row);print(json.dumps(row,ensure_ascii=True),flush=True)
(ROOT/'output/audit/current/correction-observations.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
