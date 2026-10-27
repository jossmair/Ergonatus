"""Synthesize all bundled voices with Python network connection APIs disabled."""
import base64,hashlib,json,socket,sys,threading,time,urllib.request,wave
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ergoai.voice_service import VoiceRuntime
from ergoai.translation_voices import VOICES

SAMPLES={'fr':'Bonjour, comment allez-vous ?','en':'Hello, how are you?',
 'es':'Hola, ¿cómo estás?','de':'Guten Tag, wie geht es Ihnen?',
 'it':'Buongiorno, come stai?','pt':'Olá, como está?',
 'ar':'مرحبا، كيف حالك؟','uk':'Привіт! У мене 2 книги.'}

def blocked(*args,**kwargs):raise AssertionError('Unexpected network connection during offline speech')

def main():
    socket.socket.connect=blocked;socket.socket.connect_ex=blocked
    socket.create_connection=blocked;urllib.request.urlopen=blocked
    runtime=VoiceRuntime(VOICES);report={'python_network_disabled':True,'voices':[]}
    folder=Path(__file__).resolve().parents[1]/'docs/validation/traductor-voice-samples';folder.mkdir(parents=True,exist_ok=True)
    for language,text in SAMPLES.items():
        start=time.monotonic();pcm=bytearray();rate=0
        for message in runtime.stream(dict(voice=language,text=text,rate=1),threading.Event()):
            if message['event']=='start':rate=message['rate']
            elif message['event']=='audio':pcm.extend(base64.b64decode(message['data']))
        assert pcm and any(pcm) and rate in (16000,22050,24000)
        target=folder/(language+'.wav')
        with wave.open(str(target),'wb') as audio:
            audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(rate);audio.writeframes(pcm)
        result=dict(language=language,text=text,seconds=round(time.monotonic()-start,3),
            audio_seconds=round(len(pcm)/2/rate,3),sample_rate=rate,bytes=len(pcm),sha256=hashlib.sha256(target.read_bytes()).hexdigest())
        report['voices'].append(result);print(json.dumps(result),flush=True)
    report['passed']=True
    (folder.parent/'traductor-voices-offline.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':main()
