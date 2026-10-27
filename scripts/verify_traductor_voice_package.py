"""Validate PCM from the installed multilingual voice host, in isolated data."""
import io,json,os,sys,time,uuid,wave
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

def main():
    import psutil
    os.environ['ERGONATUS_DATA']=str(ROOT/'.qa-traductor-bundled-voices')
    identity='QA-'+uuid.uuid4().hex[:8];os.environ['USERDOMAIN']=identity
    from shared.translation import speak_language
    from shared.speech import Speaker
    from shared.audio_output import AudioOutput
    from scripts.verify_traductor_voices import SAMPLES
    received=[]
    def inspect(self,data,stop):
        with wave.open(io.BytesIO(data),'rb') as audio:
            pcm=audio.readframes(audio.getnframes())
            assert pcm and any(pcm)
            received.append((len(pcm),audio.getframerate()))
    original=AudioOutput.play;AudioOutput.play=inspect
    report={'compiled_voice_host':True,'cases':[]}
    try:
        for language,text in SAMPLES.items():
            before=len(received);started=time.monotonic()
            assert speak_language(Speaker(),text,language) and len(received)>before
            result=dict(language=language,seconds=round(time.monotonic()-started,3),pcm_bytes=sum(n for n,r in received[before:]))
            report['cases'].append(result);print(json.dumps(result),flush=True)
        report['passed']=True
    finally:
        AudioOutput.play=original
        (ROOT/'docs/validation/traductor-bundled-voice-package.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        for process in psutil.process_iter(['name']):
            try:
                if process.info['name']=='ErgoTranslateVoice.exe' and process.environ().get('USERDOMAIN')==identity:process.terminate()
            except (psutil.NoSuchProcess,psutil.AccessDenied):pass

if __name__=='__main__':main()
