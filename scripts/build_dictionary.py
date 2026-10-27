"""Build a compact offline dictionary from Kaikki's French Wiktionary export."""
from pathlib import Path
import urllib.request,gzip,json,sqlite3,unicodedata,hashlib,time
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'Dictionnator/data';OUT.mkdir(parents=True,exist_ok=True)
URL='https://kaikki.org/frwiktionary/Fran%C3%A7ais/kaikki.org-dictionary-Fran%C3%A7ais.jsonl.gz'
archive=OUT/'source.jsonl.gz'
def norm(s):return unicodedata.normalize('NFC',s).casefold().replace('’',"'")
if not archive.exists():
 tmp=archive.with_suffix('.part');start=time.monotonic();total=0
 with urllib.request.urlopen(URL,timeout=90) as response,tmp.open('wb') as f:
  while chunk:=response.read(1024*1024):
   f.write(chunk);total+=len(chunk)
   if total%(25*1024*1024)==0:print('download',total//1024**2,'MiB',flush=True)
 tmp.replace(archive);print('downloaded',total,round(time.monotonic()-start,1),flush=True)
path=OUT/'dictionary.build.sqlite3';path.unlink(missing_ok=True);db=sqlite3.connect(path);db.executescript('PRAGMA journal_mode=OFF;PRAGMA synchronous=OFF;PRAGMA cache_size=-12000;CREATE TABLE entries (norm TEXT,word TEXT,pos TEXT,body TEXT);CREATE TABLE metadata (key TEXT PRIMARY KEY,value TEXT);')
count=0;senses=0
with gzip.open(archive,'rt',encoding='utf-8') as f:
 for line in f:
  item=json.loads(line)
  if item.get('lang_code')!='fr' or not item.get('word'):continue
  body=[]
  for sense in item.get('senses',[]):
   glosses=sense.get('glosses',[])
   if not glosses:continue
   record={'gloss':' — '.join(glosses),'tags':sense.get('raw_tags',[])+sense.get('topics',[])+sense.get('tags',[]),'links':[v['word'] for v in sense.get('form_of',[]) if 'word' in v]}
   examples=[v.get('text','') for v in sense.get('examples',[]) if v.get('text')];record['example']=examples[0] if examples else '';body.append(record)
  if not body:continue
  db.execute('INSERT INTO entries VALUES (?,?,?,?)',(norm(item['word']),item['word'],item.get('pos_title',item.get('pos','')),json.dumps(body,ensure_ascii=False,separators=(',',':'))));count+=1;senses+=len(body)
  if count%25000==0:db.commit();print('indexed',count,'entries',senses,'senses',flush=True)
db.execute('CREATE INDEX lookup ON entries(norm)');db.execute('CREATE INDEX spelling ON entries(word)');meta=dict(source=URL,source_page='https://kaikki.org/frwiktionary/Fran%C3%A7ais/index.html',license='CC-BY-SA 4.0 and GFDL',source_sha256=hashlib.file_digest(archive.open('rb'),'sha256').hexdigest(),entries=count,senses=senses,build_date='2026-10-26')
for k,v in meta.items():db.execute('INSERT INTO metadata VALUES (?,?)',(k,str(v)))
db.commit();assert db.execute('PRAGMA quick_check').fetchone()[0]=='ok';db.close();path.replace(OUT/'dictionary.sqlite3');(OUT/'SOURCE.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8');print('finished',meta,flush=True)
