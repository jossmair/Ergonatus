import io,json,threading
from types import SimpleNamespace
import pytest
from ergoai.accelerated_engine import AcceleratedEngine,AccelerationUnavailable,runtime_device


def runtime(tmp_path,monkeypatch):
    import hashlib
    folder=tmp_path/'ergoai/accelerator';(folder/'runtime').mkdir(parents=True)
    files={}
    for name in ['llama-server.exe','llama-server-impl.dll','ggml-vulkan.dll']:
        (folder/'runtime'/name).write_bytes(b'verified-test');files[name]=hashlib.sha256(b'verified-test').hexdigest()
    (folder/'receipt.json').write_text(json.dumps(dict(files=files)))
    monkeypatch.setattr('ergoai.accelerated_engine.suite_root',lambda:tmp_path)
    return folder


def test_discrete_gpu_selected_instead_of_integrated_gpu(tmp_path,monkeypatch):
    runtime(tmp_path,monkeypatch)
    devices=b'Vulkan0: Intel Iris Xe (8000 MiB, 7000 MiB free)\nVulkan1: NVIDIA T500 (4096 MiB, 3500 MiB free)'
    monkeypatch.setattr('ergoai.accelerated_engine.subprocess.run',lambda *a,**k:SimpleNamespace(stdout=devices,stderr=b'',returncode=0))
    _,(device,label)=runtime_device(1800*1024**2)
    assert device=='Vulkan1' and label=='NVIDIA T500'


def test_insufficient_vram_declines_without_model_loading(tmp_path,monkeypatch):
    runtime(tmp_path,monkeypatch)
    monkeypatch.setattr('ergoai.accelerated_engine.subprocess.run',lambda *a,**k:SimpleNamespace(stdout=b'Vulkan1: NVIDIA T500 (4096 MiB, 1500 MiB free)',stderr=b'',returncode=0))
    with pytest.raises(AccelerationUnavailable,match='Mémoire'):runtime_device(1800*1024**2)


def test_modified_gpu_binary_is_never_executed(tmp_path,monkeypatch):
    folder=runtime(tmp_path,monkeypatch);(folder/'runtime/ggml-vulkan.dll').write_bytes(b'changed')
    monkeypatch.setattr('ergoai.accelerated_engine.subprocess.run',lambda *a,**k:pytest.fail('Unverified executable launched'))
    with pytest.raises(AccelerationUnavailable,match='Empreinte'):runtime_device(1)


def test_cpu_override_skips_gpu_probe(monkeypatch):
    monkeypatch.setenv('ERGONATUS_GPU','0')
    with pytest.raises(AccelerationUnavailable,match='désactivée'):runtime_device(1)


def engine_response(monkeypatch,events):
    engine=AcceleratedEngine();engine.process=SimpleNamespace(poll=lambda:None)
    raw=b''.join(b'data: '+json.dumps(e).encode()+b'\n\n' if isinstance(e,dict) else b'data: '+e+b'\n\n' for e in events)
    monkeypatch.setattr(engine,'open',lambda *a,**k:io.BytesIO(raw));return engine


def test_stream_handles_usage_frames_and_null_finish_content(monkeypatch):
    engine=engine_response(monkeypatch,[dict(choices=[]),dict(choices=[dict(delta=dict(content='Texte corrigé.'))]),dict(choices=[dict(delta=dict(content=None),finish_reason='stop')]),b'[DONE]'])
    chunks=list(engine.create_chat_completion(messages=[]))
    assert ''.join(c['choices'][0]['delta']['content'] for c in chunks)=='Texte corrigé.'
    assert chunks[-1]['choices'][0]['finish_reason']=='stop'


def test_truncated_gpu_stream_never_returns_partial_success(monkeypatch):
    engine=engine_response(monkeypatch,[dict(choices=[dict(delta=dict(content='Début incomplet'))])])
    with pytest.raises(AccelerationUnavailable,match='interrompue'):list(engine.create_chat_completion(messages=[]))


def test_cancel_prevents_opening_a_request(monkeypatch):
    engine=AcceleratedEngine();engine.stop.set();monkeypatch.setattr(engine,'open',lambda *a,**k:pytest.fail('Cancelled request sent'))
    with pytest.raises(ValueError,match='annulé'):list(engine.create_chat_completion(messages=[]))


def test_cpu_fallback_preserves_model_and_context(monkeypatch):
    from ergoai.proofreading_service import Proofreader,MODEL
    import sys
    from pathlib import Path
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Redactor/source'))
    calls=[]
    class NoGPU:
        def load(self,*a,**k):raise AccelerationUnavailable('Carte occupée.')
        def close(self):pass
    class CPU:
        def load(self,path,context):calls.append((path.name,context))
    monkeypatch.setattr('ergoai.memory_budget.release_idle_peer',lambda *a:None)
    monkeypatch.setattr('ergoai.accelerated_engine.AcceleratedEngine',NoGPU)
    monkeypatch.setattr('app.ai.engine.LlamaEngine',CPU)
    host=Proofreader();host.load();assert host.backend=='CPU' and calls==[(MODEL,4096)]


def test_model_integrity_failure_is_not_hidden_by_cpu_fallback(monkeypatch):
    from ergoai.proofreading_service import Proofreader
    class Invalid:
        def load(self,*a,**k):raise ValueError('Empreinte du modèle incorrecte.')
    monkeypatch.setattr('ergoai.memory_budget.release_idle_peer',lambda *a:None)
    monkeypatch.setattr('ergoai.accelerated_engine.AcceleratedEngine',Invalid)
    host=Proofreader()
    with pytest.raises(ValueError,match='Empreinte'):host.load()
    assert host.loading_engine is None


def test_cancel_arriving_before_job_never_runs_the_job(tmp_path,monkeypatch):
    import os,sys,time,uuid,subprocess
    from pathlib import Path
    monkeypatch.setenv('ERGONATUS_DATA',str(tmp_path/'data'));monkeypatch.setenv('USERDOMAIN','CancelOrder'+uuid.uuid4().hex)
    marker=tmp_path/'job-ran';root=Path(__file__).resolve().parents[1]
    code="""from pathlib import Path
import sys
sys.path.insert(0,sys.argv[1])
from ergoai.proofreading_service import serve
class Fake:
    engine=None
    def correct(self,text,cancel):
        Path(sys.argv[2]).write_text('ran')
        return {'text':text}
    def unload(self):pass
serve(host_factory=Fake)
"""
    process=subprocess.Popen([sys.executable,'-c',code,str(root),str(marker)],env=os.environ.copy(),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    try:
        from ergoai.proofreading_client import request
        deadline=time.monotonic()+10
        while True:
            try:request({'op':'status'});break
            except (OSError,EOFError):
                assert process.poll() is None and time.monotonic()<deadline;time.sleep(.05)
        request({'op':'cancel','id':'cancel-before-job'})
        with pytest.raises(ValueError,match='annulée'):request({'op':'correct','id':'cancel-before-job','text':'Un texte.'})
        assert not marker.exists()
    finally:
        process.terminate();process.wait(timeout=5)
