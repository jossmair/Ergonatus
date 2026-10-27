"""Owned, authenticated loopback Vulkan worker for the existing GGUF model."""
import hashlib,json,os,re,secrets,socket,subprocess,tempfile,threading,time
from pathlib import Path
import urllib.request
from shared.catalog import suite_root
from shared.domain import app_data


class AccelerationUnavailable(RuntimeError):pass


def runtime_device(model_bytes):
    if os.environ.get('ERGONATUS_GPU')=='0':raise AccelerationUnavailable('Accélération désactivée.')
    base=suite_root()/'ergoai/accelerator';runtime=base/'runtime';exe=runtime/'llama-server.exe'
    if not exe.is_file() or not (base/'receipt.json').is_file():raise AccelerationUnavailable('Moteur graphique absent.')
    receipt=json.loads((base/'receipt.json').read_text(encoding='utf-8'))
    required={'llama-server.exe','llama-server-impl.dll','ggml-vulkan.dll'}
    if not required<=set(receipt.get('files',{})):raise AccelerationUnavailable('Moteur graphique incomplet.')
    for name,expected in receipt['files'].items():
        if Path(name).name!=name:raise AccelerationUnavailable('Manifeste graphique invalide.')
        path=runtime/name
        if not path.is_file():raise AccelerationUnavailable('Moteur graphique incomplet.')
        with path.open('rb') as stream:actual=hashlib.file_digest(stream,'sha256').hexdigest()
        if actual!=expected:raise AccelerationUnavailable('Empreinte du moteur graphique incorrecte.')
    try:
        probe=subprocess.run([str(exe),'--list-devices'],capture_output=True,timeout=10,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    except (OSError,subprocess.TimeoutExpired) as error:raise AccelerationUnavailable('Carte graphique indisponible.') from error
    output=(probe.stdout+probe.stderr).decode('utf-8',errors='replace')
    devices=[]
    for line in output.splitlines():
        match=re.search(r'(Vulkan\d+):\s*(.+?)\s*\([\d.]+ MiB, ([\d.]+) MiB free\)',line)
        if match and any(word in match[2].upper() for word in ('NVIDIA','AMD','RADEON')) and float(match[3])*1024**2>=model_bytes+512*1024**2:devices.append((match[1],match[2]))
    if probe.returncode or not devices:raise AccelerationUnavailable('Mémoire graphique disponible insuffisante ou carte non prise en charge.')
    return exe,devices[0]


class AcceleratedEngine:
    def __init__(self):
        self.stop=threading.Event();self.process=None;self.job=None;self.directory=None;self.llm=self;self.backend='GPU Vulkan';self._response=None
        self.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))

    @property
    def alive(self):return self.process is not None and self.process.poll() is None

    def load(self,path,context=4096):
        path=Path(path).resolve();exe,(device,label)=runtime_device(path.stat().st_size)
        # Keep the existing publisher hash and prompt template checks. GPU
        # weights do not require the CPU-only model's RAM preflight.
        import sys
        sys.path.insert(0,str(suite_root()/'Redactor/source'))
        from app.ai.model_manager import validate_model
        from app.ai.gguf import metadata,luciole_template
        validate_model(path,check_hash=True)
        template=metadata(path).get('tokenizer.chat_template')
        if not isinstance(template,str) or not template.strip():raise ValueError('Format de conversation du modèle absent.')
        self.directory=tempfile.TemporaryDirectory(prefix='gpu-',dir=app_data('ergoai'))
        folder=Path(self.directory.name);template_file=folder/'template.jinja';template_file.write_text(luciole_template(template),encoding='utf-8')
        self.key=secrets.token_hex(32);key_file=folder/'key';key_file.write_text(self.key,encoding='ascii')
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        self.url='http://127.0.0.1:'+str(port)
        args=[str(exe),'-m',str(path),'--host','127.0.0.1','--port',str(port),'--api-key-file',str(key_file),'--device',device,'-ngl','99','-c',str(context),'-np','1','--fit','off','--no-webui','--no-slots','--jinja','--chat-template-file',str(template_file),'--reasoning','off','-t','4']
        try:
            import win32job
            self.job=win32job.CreateJobObject(None,'Local\\Ergonatus.GPU.'+secrets.token_hex(16));info=win32job.QueryInformationJobObject(self.job,win32job.JobObjectExtendedLimitInformation);info['BasicLimitInformation']['LimitFlags']|=win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;win32job.SetInformationJobObject(self.job,win32job.JobObjectExtendedLimitInformation,info)
            self.process=subprocess.Popen(args,cwd=exe.parent,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            win32job.AssignProcessToJobObject(self.job,int(self.process._handle))
            deadline=time.monotonic()+45
            while time.monotonic()<deadline:
                if not self.alive:raise AccelerationUnavailable('Le moteur graphique n’a pas démarré.')
                if self.stop.is_set():raise ValueError('Traitement annulé.')
                try:
                    with self.open('/health',timeout=1) as response:
                        if json.load(response).get('status')=='ok':self.backend='GPU Vulkan · '+label;return
                except OSError:pass
                time.sleep(.1)
            raise AccelerationUnavailable('Initialisation graphique trop longue.')
        except Exception as error:
            self.close()
            if isinstance(error,(AccelerationUnavailable,ValueError)):raise
            raise AccelerationUnavailable('Accélération graphique indisponible.') from error

    def open(self,path,payload=None,timeout=20):
        request=urllib.request.Request(self.url+path,data=json.dumps(payload,ensure_ascii=False).encode() if payload is not None else None,headers={'Authorization':'Bearer '+self.key,'Content-Type':'application/json'})
        return self.opener.open(request,timeout=timeout)

    def create_chat_completion(self,messages,stream=True,**parameters):
        if not stream:raise ValueError('Le moteur utilise une réponse progressive.')
        if self.stop.is_set():raise ValueError('Traitement annulé.')
        if not self.alive:raise AccelerationUnavailable('Le moteur graphique est indisponible.')
        payload=dict(messages=messages,stream=True,cache_prompt=True,**parameters)
        try:
            with self.open('/v1/chat/completions',payload) as response:
                self._response=response;total=0;finished=False
                while True:
                    if self.stop.is_set():raise ValueError('Traitement annulé.')
                    raw=response.readline(65537);total+=len(raw)
                    if total>1048576 or len(raw)>65536:raise ValueError('Réponse du moteur trop longue.')
                    if not raw:break
                    if not raw.startswith(b'data:'):continue
                    data=raw[5:].strip()
                    if data==b'[DONE]':finished=True;break
                    item=json.loads(data)
                    if 'error' in item:raise AccelerationUnavailable('Le moteur graphique est indisponible.')
                    if not item.get('choices'):continue
                    for choice in item['choices']:
                        delta=choice.get('delta') or {};delta['content']=delta.get('content') or '';choice['delta']=delta
                    yield item
                if not finished:raise AccelerationUnavailable('Réponse graphique interrompue. Aucun remplacement.')
        except OSError as error:
            if self.stop.is_set():raise ValueError('Traitement annulé.') from error
            raise AccelerationUnavailable('Le moteur graphique est indisponible.') from error
        finally:self._response=None

    def cancel(self):
        self.stop.set()
        if self.alive:
            self.process.terminate()
            try:self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:self.process.kill();self.process.wait(timeout=2)

    def close(self):
        if self.alive:
            self.process.terminate()
            try:self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:self.process.kill();self.process.wait(timeout=5)
        self.process=None
        if self.job is not None:self.job.Close();self.job=None
        if self.directory is not None:self.directory.cleanup();self.directory=None
