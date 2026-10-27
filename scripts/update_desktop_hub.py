"""Update the desktop installation the user actually opens; preserve all user data."""
from pathlib import Path
import json,hashlib,shutil,os,subprocess,time,uuid
import psutil,win32gui,win32process,win32con
SOURCE=Path(__file__).resolve().parents[1]
TARGET=Path('C:/Users/Josselin/Desktop/Ergonatus').resolve()
assert TARGET.name=='Ergonatus' and TARGET.parent==Path('C:/Users/Josselin/Desktop').resolve()
assert (TARGET/'Hub/Ergonatus.exe').is_file() and (TARGET/'assets/orbs/ergonatus.png').is_file()
assert not TARGET.is_symlink() and not TARGET.is_junction()
for name in ('Hub','ergoai','assets','models'):
 p=TARGET/name;assert not p.is_symlink() and not p.is_junction()
backup=SOURCE/'output/audit/current'/('desktop-hub-backup-'+uuid.uuid4().hex[:8]);backup.mkdir()
def digest(path):
 with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def processes():
 result=[]
 for p in psutil.process_iter(['exe','name']):
  try:
   if p.info['exe'] and Path(p.info['exe']).resolve().is_relative_to(TARGET):result.append(p)
  except (psutil.Error,OSError):pass
 return result
hub_path=TARGET/'Hub/Ergonatus.exe';hosts=processes();frontends=[p for p in hosts if p.info['name']!='Ergonatus.exe' and not p.info['name'].startswith('Ergo')]
proof=TARGET/'ergoai/proofreading/runtime';proof_update=digest(proof/'ErgoProofread.exe')!=digest(SOURCE/'ergoai/proofreading/runtime/ErgoProofread.exe')
if proof_update and frontends:raise RuntimeError('Un logiciel utilise peut-être le moteur. Mise à jour reportée sans fermer ses documents.')
shutil.copytree(TARGET/'Hub',backup/'Hub')
if proof_update:shutil.copytree(proof,backup/'proofreading-runtime')
for name in ('suite_design.py','suite_interactions.py','suite_interactions.json'):
 if (TARGET/name).exists():shutil.copy2(TARGET/name,backup/name)
for p in hosts:
 if Path(p.info['exe']).resolve()==hub_path:
  if not frontends:
   def close(hwnd,_):
    if win32process.GetWindowThreadProcessId(hwnd)[1]==p.pid and win32gui.GetWindowText(hwnd):win32gui.PostMessage(hwnd,win32con.WM_CLOSE,0,0)
   win32gui.EnumWindows(close,None)
   try:p.wait(timeout=8)
   except psutil.TimeoutExpired:p.terminate();p.wait(timeout=5)
  else:p.terminate();p.wait(timeout=5) # only the hub; its normal Close would stop other apps
if proof_update:
 for p in processes():
  if Path(p.info['exe']).resolve()==proof/'ErgoProofread.exe':p.terminate();p.wait(timeout=5)
 shutil.copytree(SOURCE/'ergoai/proofreading/runtime',proof,dirs_exist_ok=True)
for folder in ('Dictionnator','Explicator','Tablinator'):
 assert not (TARGET/folder).is_symlink() and not (TARGET/folder).is_junction()
 shutil.copytree(SOURCE/folder,TARGET/folder,dirs_exist_ok=True)
shutil.copy2(SOURCE/'Hub/Ergonatus.exe',hub_path)
shutil.copytree(SOURCE/'Hub/_internal',TARGET/'Hub/_internal',dirs_exist_ok=True)
for name in ('suite_design.py','suite_interactions.py','suite_interactions.json'):
 shutil.copy2(SOURCE/name,TARGET/name)
(TARGET/'docs').mkdir(exist_ok=True);shutil.copy2(SOURCE/'docs/GUIDE_SUITE.md',TARGET/'docs/GUIDE_SUITE.md')
(TARGET/'scripts').mkdir(exist_ok=True);shutil.copy2(SOURCE/'scripts/windows_ocr.ps1',TARGET/'scripts/windows_ocr.ps1')
for key in ('dictionnator','explicator','tablinator','ergonatus','ergonatus-orb'):
 for ext in ('.png','.ico'):
  path=SOURCE/'assets/orbs'/(key+ext)
  if path.exists():shutil.copy2(path,TARGET/'assets/orbs'/path.name)
for name in ('Luth-1.7B-Instruct-Q8_0.gguf','LFM2-700M-Q4_K_M.gguf'):
 dst=TARGET/'models'/name;src=SOURCE/'models'/name
 if not dst.exists():shutil.copy2(src,dst);shutil.copy2(src.with_suffix('.receipt.json'),dst.with_suffix('.receipt.json'))
assert digest(TARGET/'Dictionnator/data/dictionary.sqlite3')==digest(SOURCE/'Dictionnator/data/dictionary.sqlite3')
report=dict(date='2026-10-26',target=str(TARGET),backup=str(backup),applications=21,new_apps=['Dictionnator','Explicator','Tablinator'],profiles_preserved=True,portable_archive_created=False,hub_sha256=digest(hub_path))
(TARGET/'MISE-A-JOUR-LOCALE.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');(SOURCE/'output/audit/current/desktop-hub-update.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
p=subprocess.Popen([str(hub_path),'--snapshot',str(SOURCE/'output/audit/current/captures/hub-desktop-updated.png')],cwd=TARGET,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));report['pid']=p.pid
print(json.dumps(report,ensure_ascii=False))
