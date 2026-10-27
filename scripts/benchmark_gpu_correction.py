from pathlib import Path
import sys,os,time,json,subprocess,socket,secrets,urllib.request,tempfile,re
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'Redactor/source'));OUT=ROOT/'output/correction-gpu'
from app.ai.gguf import metadata,luciole_template
from ergoai.proofreading_service import messages,validate_output,MODEL
from ergoai.correction import correct_rules
model=ROOT/'models'/MODEL;template=OUT/'model-template.jinja';template.write_text(luciole_template(metadata(model)['tokenizer.chat_template']),encoding='utf-8')
key=secrets.token_hex(32);keyfile=OUT/'test-api-key';keyfile.write_text(key)
sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];sock.close();base='http://127.0.0.1:'+str(port)
def request(path,payload=None):
    req=urllib.request.Request(base+path,data=json.dumps(payload,ensure_ascii=False).encode() if payload is not None else None,headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
    return json.load(urllib.request.urlopen(req,timeout=90))
log=(OUT/'gpu-server.log').open('w',encoding='utf-8');start=time.perf_counter();p=subprocess.Popen([str(ROOT/'ergoai/accelerator/runtime/llama-server.exe'),'-m',str(model),'--host','127.0.0.1','--port',str(port),'--api-key-file',str(keyfile),'--device','Vulkan1','-ngl','99','-c','4096','-np','1','--no-webui','--no-slots','--jinja','--chat-template-file',str(template),'--reasoning','off','-t','4'],cwd=ROOT,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
try:
    deadline=time.monotonic()+90
    while time.monotonic()<deadline:
        if p.poll() is not None:raise RuntimeError('GPU server exited '+str(p.returncode))
        try:
            if request('/health').get('status')=='ok':break
        except OSError:pass
        time.sleep(.2)
    else:raise TimeoutError('GPU loading timed out')
    load=time.perf_counter()-start;rows=[];print('load_seconds',load,flush=True)
    texts=["Hier, je suis aller au magasin avec mes amis. On a acheter plusieurs chose mais les prix était trop chère. Ensuite, nous somme rentrer chez nous parce qu'il commencer à pleuvoir. J'ai oublier mon sac dans la voiture et personne ne la retrouver. Demain, je retournerais le chercher si j'ai le temp.",'testes pour voir si sa marchent ici la corection gramaticales','Les petite fille joue dans le jardin.']
    for source in texts:
        start=time.perf_counter();prepared=correct_rules(source);parts=[]
        for part in re.split(r'(\r?\n+|(?<=[.!?…])[ \t]+)',prepared['text']):
            if not part or part.isspace():parts.append(part);continue
            result=request('/v1/chat/completions',dict(messages=messages(part),max_tokens=min(768,max(192,len(part))),temperature=0,repeat_penalty=1.0,cache_prompt=True,stream=False))
            choice=result['choices'][0];assert choice['finish_reason']!='length';parts.append(validate_output(part,choice['message']['content'].strip()))
        final=correct_rules(''.join(parts));row=dict(source=source,text=final['text'],remaining=final['remaining'],seconds=round(time.perf_counter()-start,3));rows.append(row);print(json.dumps(row,ensure_ascii=True),flush=True)
    (OUT/'gpu-benchmark.json').write_text(json.dumps(dict(load_seconds=load,results=rows),ensure_ascii=False,indent=2),encoding='utf-8')
finally:
    p.terminate();p.wait(timeout=10);log.close();keyfile.unlink(missing_ok=True)
