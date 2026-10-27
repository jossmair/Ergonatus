from pathlib import Path
import shutil, json, hashlib
root=Path.cwd(); dst=root/'Ergonatus'
apps=[('Fortinatus','Claviernator','dist/orbes-liees/Claviernator-1.3.10'),('Precisionator','Precisionator','dist/orbes-liees/Precisionator-1.0.7'),('Transcri','Transcrinator','dist/orbes-liees/Transcrinator-1.3.17'),('Redactor','Redactor','dist/Redactor-0.4.1')]
ignore=shutil.ignore_patterns('.git','.venv','dist','build','archive','models','runtimes','vendor','tools','sdk','__pycache__','.pytest_cache','.test*','*.zip','*.gguf','*.onnx')
manifest=[]
for src,name,release in apps:
    target=dst/name; target.mkdir(exist_ok=True)
    shutil.copytree(root/src,target/'source',ignore=ignore,dirs_exist_ok=True)
    shutil.copytree(root/src/release,target/'runtime',dirs_exist_ok=True)
    exe=target/'runtime'/f'{name}.exe'
    manifest.append({'id':name.lower(),'source':src,'release':release,'executable':str(exe.relative_to(dst)), 'sha256':hashlib.sha256(exe.read_bytes()).hexdigest()})
    print(name, 'copié',flush=True)
hub=dst/'Hub'; hub.mkdir(exist_ok=True)
shutil.copytree(root/'Fortinator/src',hub/'fortinator_reference/src',ignore=shutil.ignore_patterns('bin','obj'),dirs_exist_ok=True)
shutil.copytree(root/'Fortinator/docs',hub/'fortinator_reference/docs',dirs_exist_ok=True)
shutil.copy2(root/'Fortinator/README.md',hub/'fortinator_reference/README.md')
ai=dst/'ergoai'; ai.mkdir(exist_ok=True)
bundle=ai/'transcription'; bundle.mkdir(exist_ok=True)
for name in ['models','runtimes']:
    shutil.copytree(root/'Transcri/dist/Transcrinator-1.3.16'/name,bundle/name,dirs_exist_ok=True)
for name in ['bundle.json','LICENSE']:
    shutil.copy2(root/'Transcri/dist/Transcrinator-1.3.16'/name,bundle/name)
models=dst/'models'; models.mkdir(exist_ok=True)
for name in ['LFM2-700M-Q4_K_M.gguf','LFM2-700M-Q4_K_M.receipt.json']:
    shutil.copy2(root/'Redactor/models'/name,models/name)
(dst/'docs/ASSEMBLY.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('Assemblage terminé',flush=True)
