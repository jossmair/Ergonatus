"""Exercise the delivered voice executable without changing the user's clipboard."""
from pathlib import Path
import os,sys,uuid,time,threading,subprocess,json,io,wave
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
os.environ['USERDOMAIN']='ErgoVoiceQA-'+uuid.uuid4().hex
os.environ['ERGONATUS_DATA']=str(root/'.test-data'/os.environ['USERDOMAIN'])
from shared.neural_speech import status,warm,stream
process=subprocess.Popen([str(root/'ergoai/voice/runtime/ErgoVoice.exe')],cwd=root)
results=[]
try:
    for attempt in range(150):
        try:status();break
        except OSError:time.sleep(.1)
    else:raise RuntimeError('Voice executable did not start')
    for gender in ('Femme','Homme'):
        voice=gender+' · naturelle';start=time.monotonic();warm(voice);prepared=time.monotonic()-start
        chunks=[];first=[];start=time.monotonic()
        def receive(data):
            if not first:first.append(time.monotonic()-start)
            chunks.append(data)
        assert stream('Bonjour. Avec Lector, sélectionnez un passage pour écouter le texte à votre rythme.',voice,0,threading.Event(),play=receive)
        pcm=[]
        for data in chunks:
            with wave.open(io.BytesIO(data),'rb') as source:
                rate=source.getframerate();pcm.append(source.readframes(source.getnframes()))
        assert pcm and sum(map(len,pcm))>1000
        target=root/'docs/validation'/('lector-voix-'+gender.lower()+'.wav')
        with wave.open(str(target),'wb') as output:
            output.setnchannels(1);output.setsampwidth(2);output.setframerate(rate);output.writeframes(b''.join(pcm))
        results.append(dict(voice=voice,preparation_seconds=prepared,first_audio_seconds=first[0],synthesis_seconds=time.monotonic()-start,audio_seconds=sum(map(len,pcm))/(rate*2)))
    stop=threading.Event();stop.set()
    assert stream('Ne doit pas être lu.','Homme · naturelle',0,stop,play=lambda data:(_ for _ in ()).throw(AssertionError())) is False
    (root/'docs/validation/lector-voices.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    print(json.dumps(results,indent=2))
finally:
    process.terminate();process.wait(timeout=10)
