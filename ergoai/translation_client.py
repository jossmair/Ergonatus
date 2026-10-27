"""Authenticated, cancellable local translation calls. No network/downloads."""
import json,subprocess,sys,threading,time,uuid
from multiprocessing.connection import Client
from shared.catalog import suite_root
from ergoai.service import authkey
from ergoai.translation_service import endpoint

_lock=threading.Lock()

def request(payload,timeout=5):
    with Client(endpoint(),family='AF_PIPE',authkey=authkey()) as connection:
        connection.send_bytes(json.dumps(payload,ensure_ascii=False).encode())
        if not connection.poll(timeout):raise ValueError('Le moteur de traduction ne répond pas.')
        result=json.loads(connection.recv_bytes(131072))
    if not result.get('ok'):raise ValueError(result.get('error','Traduction indisponible.'))
    return result

def ensure():
    try:return request(dict(op='status'))
    except (OSError,EOFError,FileNotFoundError):pass
    with _lock:
        try:return request(dict(op='status'))
        except (OSError,EOFError,FileNotFoundError):pass
        root=suite_root();exe=root/'ergoai/proofreading/runtime/ErgoProofread.exe'
        if exe.exists():args=[str(exe)]
        elif not getattr(sys,'frozen',False):args=[sys.executable,str(root/'run_proofreader.py')]
        else:raise ValueError('Le moteur de traduction doit être installé.')
        subprocess.Popen(args,cwd=root,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        for _ in range(150):
            time.sleep(.1)
            try:return request(dict(op='status'))
            except (OSError,EOFError,FileNotFoundError):pass
    raise ValueError('Le moteur de traduction n’a pas démarré.')

def translate(text,source,target,cancel=None):
    if cancel and cancel.is_set():raise ValueError('Traduction annulée.')
    ensure();identifier=uuid.uuid4().hex
    with Client(endpoint(),family='AF_PIPE',authkey=authkey()) as connection:
        connection.send_bytes(json.dumps(dict(op='translate',text=text,source=source,target=target,id=identifier),ensure_ascii=False).encode())
        deadline=time.monotonic()+180
        while not connection.poll(.1):
            if cancel and cancel.is_set():
                request(dict(op='cancel',id=identifier));raise ValueError('Traduction annulée.')
            if time.monotonic()>deadline:
                request(dict(op='cancel',id=identifier));raise ValueError('Le passage est trop long pour le délai de traduction.')
        result=json.loads(connection.recv_bytes(131072))
    if not result.get('ok'):raise ValueError(result.get('error','Traduction indisponible.'))
    return result
