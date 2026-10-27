"""Offline bundled voices, without Windows voices or network fallback."""
import io,json,subprocess,threading,wave
from multiprocessing.connection import Client
from shared.catalog import suite_root
from ergoai.service import authkey
from ergoai.translation_voice_service import endpoint

_launch_lock=threading.Lock()

def prepare_playback(data):
    """Wake the audio device before speech, preserving every original PCM byte."""
    with wave.open(io.BytesIO(data),'rb') as source:
        channels,width,rate=source.getnchannels(),source.getsampwidth(),source.getframerate()
        pcm=source.readframes(source.getnframes())
    if width!=2 or channels not in (1,2):raise ValueError('Format vocal non pris en charge.')
    output=io.BytesIO();frame_size=channels*width
    with wave.open(output,'wb') as audio:
        audio.setnchannels(channels);audio.setsampwidth(width);audio.setframerate(rate)
        audio.writeframes(bytes(round(rate*.4)*frame_size)+pcm+bytes(round(rate*.08)*frame_size))
    return output.getvalue()

def connect():return Client(endpoint(),family='AF_PIPE',authkey=authkey())

def status():
    with connect() as connection:
        connection.send_bytes(b'{"op":"status"}')
        if not connection.poll(2):raise ValueError('La voix locale ne répond pas.')
        return json.loads(connection.recv_bytes(1024))

def ensure_service(stop):
    if stop.is_set():return
    try:return status()
    except (OSError,EOFError,FileNotFoundError):pass
    with _launch_lock:
        try:return status()
        except (OSError,EOFError,FileNotFoundError):pass
        root=suite_root();exe=root/'ergoai/translation_voice/runtime/ErgoTranslateVoice.exe'
        if exe.is_file():args=[str(exe)]
        else:
            python=root/'ergoai/voice/.venv/Scripts/python.exe'
            if not python.is_file():raise ValueError('Le moteur vocal de Traductor est absent. Réinstallez le dossier complet.')
            args=[str(python),str(root/'run_translation_voice.py')]
        subprocess.Popen(args,cwd=root,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        for _ in range(150):
            if stop.wait(.1):return
            try:return status()
            except (OSError,EOFError,FileNotFoundError):pass
    raise ValueError('Le moteur vocal local ne démarre pas.')

def cancel(identifier):
    try:
        with connect() as connection:
            connection.send_bytes(json.dumps(dict(op='cancel',id=identifier)).encode())
    except (OSError,EOFError,FileNotFoundError):pass

def speak(speaker,text,language):
    import sys
    from ergoai.translation_voices import VOICES
    from shared.neural_speech import stream
    from shared.audio_output import AudioOutput
    if language not in VOICES:raise ValueError('Langue de lecture inconnue.')
    filename,_=VOICES[language];path=suite_root()/'ergoai/voices'/filename
    if not path.is_file() or not path.with_suffix('.onnx.json').is_file():
        raise ValueError('La voix intégrée est absente. Réinstallez le dossier complet de Traductor.')
    if speaker.stop.is_set():return False
    if speaker.audio is None:speaker.audio=AudioOutput()
    return stream(text,language,0,speaker.stop,play=lambda data:speaker.audio.play(prepare_playback(data),speaker.stop),backend=sys.modules[__name__])
