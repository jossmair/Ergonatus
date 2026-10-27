"""Real frozen voice service: paragraph pauses and cancellation; silent playback."""
from pathlib import Path
import os,sys,uuid,time,threading,subprocess,json
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
os.environ['USERDOMAIN']='LectorCalmQA-'+uuid.uuid4().hex;os.environ['ERGONATUS_DATA']=str(root/'.test-data'/os.environ['USERDOMAIN'])
from shared.neural_speech import status,warm,stream
process=subprocess.Popen([str(root/'ergoai/voice/runtime/ErgoVoice.exe')],cwd=root)
try:
    for attempt in range(200):
        try:status();break
        except OSError:time.sleep(.1)
    warm('Femme · naturelle');starts=[]
    assert stream('Un premier paragraphe.\n\nUn second paragraphe.','Femme · naturelle',-1,threading.Event(),play=lambda data:starts.append(time.monotonic()))
    assert len(starts)>=2 and starts[1]-starts[0]>=.75,starts
    stop=threading.Event();played=[];stopped=[]
    def first(data):
        played.append(time.monotonic());threading.Timer(.12,stop.set).start()
    assert stream('Premier passage.\n\nNe pas lire ce passage après annulation.','Femme · naturelle',-1,stop,play=first) is False
    elapsed=time.monotonic()-played[0];assert len(played)==1 and elapsed<.8
    report=dict(paragraph_gap_seconds=starts[1]-starts[0],cancel_during_pause_seconds=elapsed,second_paragraph_cancelled=True,audible_playback=False)
    (root/'docs/validation/lector-calm.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
finally:process.terminate();process.wait(timeout=10)
