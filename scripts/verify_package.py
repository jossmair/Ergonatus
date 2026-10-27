"""Disposable hub launch, actual memory/time samples; no companion launch."""
import json
import os
from pathlib import Path
import subprocess
import time
import psutil
import uuid

root=Path(__file__).resolve().parents[1]
report={}
started=time.perf_counter()
environment=os.environ.copy();environment['USERDOMAIN']='ErgonatusHubTest-'+uuid.uuid4().hex
process=subprocess.Popen([str(root/'Hub/Ergonatus.exe'),'--smoke-test','--data-dir',str(root/'.test-data/package'),
                          '--snapshot',str(root/'docs/validation/hub-packaged.png')],cwd=root,env=environment)
samples=[]
while process.poll() is None and time.perf_counter()-started<30:
    try:
        p=psutil.Process(process.pid)
        samples.append(dict(seconds=round(time.perf_counter()-started,3),rss_bytes=p.memory_info().rss,cpu_seconds=sum(p.cpu_times()[:2])))
    except psutil.Error:
        pass
    time.sleep(.1)
if process.poll() is None:
    raise RuntimeError('Le smoke-test du hub ne se ferme pas dans les 30 secondes.')
report=dict(exit_code=process.returncode,elapsed_seconds=round(time.perf_counter()-started,3),
            peak_sampled_rss_bytes=max((s['rss_bytes'] for s in samples),default=0),samples=samples,
            snapshot_exists=(root/'docs/validation/hub-packaged.png').is_file(),
            scope='Hub only; cold start smoke test, no inference or companion activation.')
(root/'docs/validation/package.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='samples'},indent=2))
raise SystemExit(0 if process.returncode==0 and report['snapshot_exists'] else 1)
