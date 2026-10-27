import base64,io,json,subprocess,threading,time,uuid,wave
from multiprocessing.connection import Client
from ergoai.service import authkey
from ergoai.voice_service import endpoint
from shared.catalog import suite_root

_launch_lock=threading.Lock()

def connect():return Client(endpoint(),family='AF_PIPE',authkey=authkey())
def status():
    with connect() as connection:
        connection.send_bytes(b'{"op":"status"}')
        if not connection.poll(2):raise ValueError('La voix ne répond pas.')
        return json.loads(connection.recv_bytes(1024))

def ensure_service(stop):
    try:return status()
    except (OSError,EOFError,FileNotFoundError):pass
    with _launch_lock:
        try:return status()
        except (OSError,EOFError,FileNotFoundError):pass
        root=suite_root();exe=root/'ergoai/voice/runtime/ErgoVoice.exe'
        if exe.is_file():args=[str(exe)]
        else:
            python=root/'ergoai/voice/.venv/Scripts/python.exe'
            if not python.is_file():raise ValueError('Les voix naturelles ne sont pas installées.')
            args=[str(python),str(root/'run_ergovoice.py')]
        subprocess.Popen(args,cwd=root,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        for _ in range(100):
            if stop.wait(.1):return
            try:return status()
            except (OSError,EOFError,FileNotFoundError):pass
    raise ValueError('Le moteur vocal ne démarre pas.')

def cancel(identifier):
    try:
        with connect() as connection:connection.send_bytes(json.dumps(dict(op='cancel',id=identifier)).encode())
    except (OSError,EOFError,FileNotFoundError):pass

def warm(voice):
    ensure_service(threading.Event())
    with connect() as connection:
        connection.send_bytes(json.dumps(dict(op='warm',voice=voice)).encode())
        if not connection.poll(30):raise ValueError('La voix met trop de temps à se préparer.')
        result=json.loads(connection.recv_bytes(2048))
        if not result.get('ok'):raise ValueError(result.get('error','Voix indisponible.'))

def stream(text,voice,rate,stop,on_segment=None,play=None,backend=None):
    import sys
    api=backend or sys.modules[__name__]
    api.ensure_service(stop)
    if stop.is_set():return False
    if play is None:
        from shared.audio_output import AudioOutput
        output=AudioOutput();play=lambda data:output.play(data,stop)
    identifier=uuid.uuid4().hex
    with api.connect() as connection:
        connection.send_bytes(json.dumps(dict(op='speak',id=identifier,text=text,voice=voice,rate=rate)).encode())
        pcm=bytearray();sample_rate=22050;phrase='';pause=0;last=time.monotonic()
        try:
            while not stop.is_set():
                if not connection.poll(.05):
                    if time.monotonic()-last>60:raise ValueError('La synthèse vocale prend trop de temps.')
                    continue
                message=json.loads(connection.recv_bytes(131072));last=time.monotonic()
                if not message.get('ok'):raise ValueError(message.get('error','Voix indisponible.'))
                event=message.get('event')
                if event=='start':
                    sample_rate=message['rate'];phrase=message['text'];pcm.clear()
                    pause=message.get('pause_before',0)
                    if not isinstance(pause,(int,float)) or not 0<=pause<=3:raise ValueError('Pause vocale invalide.')
                    if sample_rate not in (16000,22050,24000,44100,48000):raise ValueError('Format audio inconnu.')
                elif event=='audio':
                    pcm.extend(base64.b64decode(message['data'],validate=True))
                    if len(pcm)>8*1024*1024:raise ValueError('Segment vocal trop long.')
                elif event=='end':
                    if stop.is_set():break
                    output=io.BytesIO()
                    with wave.open(output,'wb') as wav:
                        wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(sample_rate);wav.writeframes(bytes(pcm))
                    if pause and stop.wait(pause):break
                    if on_segment:on_segment(phrase)
                    if not stop.is_set():play(output.getvalue())
                elif event=='done':return not message.get('cancelled',False)
        finally:
            if stop.is_set():threading.Thread(target=api.cancel,args=(identifier,),daemon=True).start()
    return False
