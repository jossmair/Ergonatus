"""Exercise the packaged shared daemon, including Redactor's real streaming adapter."""
from pathlib import Path
import os,sys,json,time,uuid
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
os.environ['ERGONATUS_DATA']=str(ROOT/'.test-data/ai-release-v2');os.environ['ERGONATUS_SHARED_AI']='1'
from ergoai.client import infer,ensure_service
from ergoai.service import request,endpoint,authkey
from multiprocessing.connection import Client
report={'initial':ensure_service()}
report['correction']=infer('correct','Les réunion sont terminé.','release-correction')
report['translation']=infer('translate','Bonjour, je voudrais un verre d’eau.','release-translation','English')
assert 'réunions' in report['correction']['text'] and 'terminées' in report['correction']['text']
assert 'water' in report['translation']['text'].lower()
sys.path.insert(0,str(ROOT/'Redactor/source'))
from app.ai.engine import LlamaEngine
from app.ai.prompts import Request
engine=LlamaEngine();engine.load(ROOT/'models/LFM2-700M-Q4_K_M.gguf')
assert engine.llm is None
parts=list(engine.stream(Request('correct','Les réunion sont terminé.'),128))
report['redactor_shared_stream']=dict(text=''.join(parts),pieces=len(parts),private_model_loaded=engine.llm is not None,metrics=vars(engine.metrics))
assert len(parts)>1 and 'réunions' in ''.join(parts)
engine.close()
identifier=uuid.uuid4().hex
with Client(endpoint(),family='AF_PIPE',authkey=authkey()) as connection:
    connection.send_bytes(json.dumps(dict(op='compose',id=identifier,text='Rédige un très long récit de voyage, en mille mots.',stream=True)).encode())
    assert connection.poll(20);first=json.loads(connection.recv_bytes(262144));assert first.get('event')=='token'
    request(dict(op='cancel',id=identifier));cancelled=False
    for _ in range(1000):
        if not connection.poll(10):break
        message=json.loads(connection.recv_bytes(262144))
        if not message.get('ok'):cancelled='annul' in message.get('error','');break
        if message.get('event')=='done':break
    report['cancellation']=cancelled
    assert cancelled
report['unload']=request(dict(op='unload',id=uuid.uuid4().hex))
assert report['unload']['loaded'] is False
(ROOT/'docs/validation/ai-packaged-v2.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps(report,ensure_ascii=True),flush=True)
