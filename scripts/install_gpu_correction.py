from pathlib import Path
import sys,os,time,shutil,hashlib,json,psutil
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));TARGET=Path('C:/Users/Josselin/Desktop/Ergonatus');OUT=ROOT/'output/correction-gpu';BACKUP=OUT/'rollback';BACKUP.mkdir(exist_ok=True)
from shared import catalog
catalog.suite_root=lambda:TARGET
from ergoai.proofreading_client import request
deadline=time.monotonic()+65
while True:
    try:
        state=request(dict(op='release_idle'))
        if state.get('released'):break
    except (OSError,EOFError,FileNotFoundError):break
    if time.monotonic()>deadline:raise SystemExit('Traitement utilisateur en cours : installation différée, aucune interruption.')
    time.sleep(.3)
paths={base/relative for base in [ROOT,TARGET] for relative in ['ergoai/proofreading/runtime/ErgoProofread.exe','ergoai/translation/runtime/ErgoTranslate.exe']}
username=psutil.Process().username()
for p in psutil.process_iter(['exe','username']):
    try:
        if p.info['exe'] and Path(p.info['exe']).resolve() in paths and p.info['username']==username:p.terminate();p.wait(timeout=8)
    except psutil.NoSuchProcess:pass
records=[]
for package,relative,exe in [('.package-proofreader/ErgoProofread','ergoai/proofreading/runtime','ErgoProofread.exe'),('.package-translation/ErgoTranslate','ergoai/translation/runtime','ErgoTranslate.exe')]:
    source=ROOT/package;assert (source/exe).exists()
    for base in [ROOT,TARGET]:
        destination=base/relative
        if base==TARGET:
            old=destination/exe;sha=hashlib.sha256(old.read_bytes()).hexdigest();shutil.copy2(old,BACKUP/(exe+'.'+sha));records.append(dict(path=str(old),before=sha,after=hashlib.sha256((source/exe).read_bytes()).hexdigest()))
        shutil.copytree(source/'_internal',destination/'_internal',dirs_exist_ok=True);shutil.copy2(source/exe,destination/exe)
shutil.copytree(ROOT/'ergoai/accelerator',TARGET/'ergoai/accelerator',dirs_exist_ok=True)
metadata=TARGET/'MISE-A-JOUR-LOCALE.json';data=json.loads(metadata.read_text(encoding='utf-8-sig'));data.update(correction_acceleration='GPU Vulkan automatique · NVIDIA T500',correction_acceleration_release='llama.cpp b11912',correction_model='Luth-1.7B-Instruct-Q8_0.gguf',correction_cpu_fallback=True);metadata.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'installed.json').write_text(json.dumps(records,indent=2),encoding='utf-8');print('GPU correction installed. UI processes and user documents preserved.')
