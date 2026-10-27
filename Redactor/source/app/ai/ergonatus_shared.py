"""Optional shared-service transport. The standalone local engine stays available."""
from pathlib import Path
import hashlib,json,os,subprocess,threading,time,uuid
from multiprocessing.connection import Client

class SharedEngine:
    def __init__(self,context=2048,threads=0):
        self.context=context
        self.threads=threads
        import sys
        self.root=next((p for p in Path(sys.executable).resolve().parents if (p/'ergoai/runtime/ErgoAI.exe').is_file()),None)
        if self.root is None:
            self.root=next((p for p in Path(__file__).resolve().parents if (p/'ergoai/runtime/ErgoAI.exe').is_file()),None)
        if self.root is None:raise ValueError('Le service partagé Ergonatus est absent.')
        self.data=Path(os.environ.get('ERGONATUS_DATA',str(Path(os.environ.get('LOCALAPPDATA',Path.home()))/'Ergonatus')))/'ergoai'
        identity=os.environ.get('USERDOMAIN','')+'\\'+os.environ.get('USERNAME','local')+str(self.data.resolve())
        self.address=r'\\.\pipe\Ergonatus.AI.v1.'+hashlib.sha256(identity.encode()).hexdigest()[:16]
        self.identifier=None;self.metrics={}
        try:self.control(dict(op='status'))
        except (OSError,EOFError):
            subprocess.Popen([str(self.root/'ergoai/runtime/ErgoAI.exe')],cwd=self.root,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            for _ in range(100):
                time.sleep(.1)
                try:self.control(dict(op='status'));break
                except (OSError,EOFError):pass
            else:raise ValueError('Le moteur partagé ne répond pas.')
    def connect(self):return Client(self.address,family='AF_PIPE',authkey=(self.data/'auth.key').read_bytes())
    def control(self,payload):
        with self.connect() as connection:
            connection.send_bytes(json.dumps(payload).encode())
            if not connection.poll(10):raise ValueError('Le service ne répond pas.')
            result=json.loads(connection.recv_bytes(262144))
            if not result.get('ok'):raise ValueError(result.get('error','Service indisponible.'))
            return result
    def stream(self,messages,stop,max_tokens=384):
        self.identifier=uuid.uuid4().hex;cancelled=False;started=time.monotonic()
        with self.connect() as connection:
            connection.send_bytes(json.dumps(dict(op='conversation',id=self.identifier,messages=messages,max_tokens=max_tokens,context=self.context,threads=self.threads,stream=True)).encode())
            while time.monotonic()-started<180:
                if stop.is_set() and not cancelled:self.cancel();cancelled=True
                if not connection.poll(.1):continue
                result=json.loads(connection.recv_bytes(262144))
                if not result.get('ok'):
                    if stop.is_set():break
                    raise ValueError(result.get('error','Génération interrompue.'))
                if result.get('event')=='token':yield result['text']
                else:self.metrics=result.get('metrics',{});break
            else:raise ValueError('La génération a dépassé le délai maximal.')
        self.identifier=None
    def cancel(self):
        identifier=self.identifier
        if not identifier:return
        def send():
            try:self.control(dict(op='cancel',id=identifier))
            except Exception:pass
        threading.Thread(target=send,daemon=True).start()
