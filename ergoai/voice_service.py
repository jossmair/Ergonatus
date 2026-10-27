"""Local neural speech, authenticated JSON/PCM frames, no external requests."""
import base64,hashlib,json,re,threading,time
from multiprocessing.connection import Listener
from ergoai.service import endpoint as ai_endpoint,authkey
from ergoai.voice_models import VOICES
from shared.catalog import suite_root

def endpoint():return ai_endpoint().replace('Ergonatus.AI.v1.','Ergonatus.Voice.v1.')

def phrases(text):
    for paragraph in re.split(r'\n\s*\n',text):
        paragraph=re.sub(r'\s+',' ',paragraph).strip()
        while len(paragraph)>700:
            cut=max(paragraph.rfind(mark,0,650) for mark in ('. ','! ','? ','; ',': '))
            if cut<80:cut=paragraph.rfind(' ',0,650)
            if cut<1:cut=650
            else:cut+=1
            yield paragraph[:cut].strip();paragraph=paragraph[cut:].strip()
        if paragraph:yield paragraph

def reading_segments(text):
    first=True
    for paragraph in re.split(r'\n\s*\n',text):
        paragraph_first=True
        for phrase in phrases(paragraph):
            yield phrase,(.8 if not first and paragraph_first else 0)
            first=False;paragraph_first=False

def length_scale(rate):return max(.85,min(2.0,1.25*(1-rate*.07)))

class VoiceRuntime:
    def __init__(self,voices=VOICES):self.voices=voices;self.voice=None;self.label=None;self.last=time.monotonic();self.lock=threading.Lock()
    def load(self,label):
        if self.label==label and self.voice is not None:return
        from piper import PiperVoice
        from piper.config import PiperConfig
        import onnxruntime as ort
        import os
        filename,expected=self.voices[label];path=suite_root()/'ergoai/voices'/filename
        digest=hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
        if digest.hexdigest()!=expected:raise ValueError('Empreinte de la voix incorrecte.')
        self.voice=None;self.label=None
        options=ort.SessionOptions();options.intra_op_num_threads=max(1,min(4,(os.cpu_count() or 2)//2));options.inter_op_num_threads=1
        self.voice=PiperVoice(config=PiperConfig.from_dict(json.loads(path.with_suffix('.onnx.json').read_text(encoding='utf-8'))),session=ort.InferenceSession(str(path),sess_options=options,providers=['CPUExecutionProvider']));self.label=label
    def stream(self,job,cancel):
        from piper import SynthesisConfig
        if cancel.is_set():return
        self.load(job['voice']);self.last=time.monotonic()
        config=SynthesisConfig(length_scale=length_scale(job.get('rate',0)))
        for text,pause in reading_segments(job['text']):
            if cancel.is_set():break
            for chunk in self.voice.synthesize(text,syn_config=config):
                if cancel.is_set():return
                yield dict(event='start',rate=chunk.sample_rate,text=text,pause_before=pause)
                pause=0
                audio=chunk.audio_int16_bytes
                for offset in range(0,len(audio),48000):
                    if cancel.is_set():return
                    yield dict(event='audio',data=base64.b64encode(audio[offset:offset+48000]).decode('ascii'))
                yield dict(event='end')
        self.last=time.monotonic()

def main(address=endpoint,voices=VOICES):
    runtime=VoiceRuntime(voices);jobs={};guard=threading.Lock();authkey(create=True)
    def handle(connection):
        identifier=None;registered=False
        try:
            if not connection.poll(5):return
            job=json.loads(connection.recv_bytes(131072));op=job.get('op')
            if op=='status':connection.send_bytes(b'{"ok":true}');return
            if op=='warm' and job.get('voice') in voices:
                with runtime.lock:runtime.load(job['voice']);runtime.last=time.monotonic()
                connection.send_bytes(b'{"ok":true}');return
            identifier=job.get('id')
            if not isinstance(identifier,str) or not re.fullmatch('[a-f0-9]{32}',identifier):raise ValueError('Demande vocale invalide.')
            if op=='cancel':
                with guard:
                    if identifier in jobs:jobs[identifier].set()
                connection.send_bytes(b'{"ok":true}');identifier=None;return
            if op!='speak' or job.get('voice') not in voices or not isinstance(job.get('text'),str) or not 1<=len(job['text'])<=24000 or type(job.get('rate',0)) is not int or not -5<=job.get('rate',0)<=5:raise ValueError('Texte ou voix invalide.')
            cancel=threading.Event()
            with guard:
                if identifier in jobs:raise ValueError('Lecture déjà demandée.')
                jobs[identifier]=cancel
                registered=True
            if not runtime.lock.acquire(timeout=15):raise ValueError('La voix termine une autre lecture. Réessayez.')
            try:
                for message in runtime.stream(job,cancel):connection.send_bytes(json.dumps(dict(ok=True,**message)).encode())
                connection.send_bytes(json.dumps(dict(ok=True,event='done',cancelled=cancel.is_set())).encode())
            finally:runtime.lock.release()
        except (EOFError,OSError):pass
        except Exception as error:
            try:connection.send_bytes(json.dumps(dict(ok=False,error=str(error))).encode())
            except (EOFError,OSError):pass
        finally:
            if identifier and registered:
                with guard:jobs.pop(identifier,None)
            connection.close()
    def idle():
        while True:
            time.sleep(10)
            if time.monotonic()-runtime.last>180 and runtime.lock.acquire(False):
                try:runtime.voice=None;runtime.label=None
                finally:runtime.lock.release()
    threading.Thread(target=idle,daemon=True).start()
    with Listener(address(),family='AF_PIPE',authkey=authkey()) as server:
        while True:threading.Thread(target=handle,args=(server.accept(),),daemon=True).start()

if __name__=='__main__':main()
