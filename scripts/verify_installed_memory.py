from pathlib import Path
import os,sys,tempfile,uuid,time,threading,json,psutil
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));OUT=ROOT/'output/audit/2026-10-26-visual-speed';TARGET=Path('C:/Users/Josselin/Desktop/Ergonatus')
identity='MemoryProtocol'+uuid.uuid4().hex;os.environ.update(USERDOMAIN=identity,ERGONATUS_DATA=tempfile.mkdtemp())
from shared import catalog
catalog.suite_root=lambda:TARGET
rows={}
try:
    from ergoai.proofreading_client import ensure,request,correct
    ensure();box={}
    def run():
        try:box['result']=correct('Les petites filles jouent dans le jardin.')
        except Exception as e:box['error']=str(e)
    worker=threading.Thread(target=run);worker.start();deadline=time.monotonic()+45
    while worker.is_alive() and not request({'op':'status'})['loaded'] and time.monotonic()<deadline:time.sleep(.05)
    if worker.is_alive() and request({'op':'status'})['loaded']:
        rows['active_job_protected']=not request({'op':'release_idle'})['released']
        assert rows['active_job_protected']
    worker.join(50);assert not worker.is_alive()
    rows['job']=box
    rows['idle_model_released']=request({'op':'release_idle'})['released'] and not request({'op':'status'})['loaded']
    assert rows['idle_model_released']
    from ergoai.client import ensure_service
    from ergoai.service import request as general_request
    ensure_service();rows['general_service_release_protocol']=general_request({'op':'release_idle'})['released'];assert rows['general_service_release_protocol']
    (OUT/'installed-memory-protocol.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(rows,ensure_ascii=True))
finally:
    for p in psutil.process_iter(['exe']):
        try:
            if p.info['exe'] and Path(p.info['exe']).is_relative_to(TARGET/'ergoai') and p.environ().get('USERDOMAIN')==identity:p.terminate();p.wait(timeout=8)
        except (psutil.Error,OSError):pass
