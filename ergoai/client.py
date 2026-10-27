import subprocess
import sys
import time
import threading
from shared.catalog import suite_root
from ergoai.service import request

_lock=threading.Lock()

def ensure_service():
    try:return request({'op':'status'})
    except (OSError,EOFError,FileNotFoundError):pass
    with _lock:
        try:return request({'op':'status'})
        except (OSError,EOFError,FileNotFoundError):pass
        root=suite_root();exe=root/'ergoai/runtime/ErgoAI.exe'
        args=[str(exe)] if exe.exists() else [sys.executable,str(root/'run_ergoai.py')]
        if getattr(sys,'frozen',False) and not exe.exists():raise ValueError('Le moteur partagé doit être installé dans ergoai/runtime.')
        subprocess.Popen(args,cwd=root,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        for _ in range(100):
            time.sleep(.1)
            try:return request({'op':'status'})
            except (OSError,EOFError,FileNotFoundError):pass
    raise ValueError('Le moteur IA ne répond pas. Consultez les diagnostics.')

def infer(op,text,identifier,language=''):
    ensure_service()
    return request(dict(op=op,text=text,id=identifier,language=language))

def cancel(identifier):
    try:request(dict(op='cancel',id=identifier))
    except (OSError,ValueError,EOFError):pass
