from pathlib import Path
import sys,os
root=Path(SPECPATH).parent
sys.path.insert(0,str(root))
from shared.ui.theme import APP_THEMES
selected=set(filter(None,os.environ.get('ERGONATUS_BUILD_APP','').split(',')))
extra_excludes=[]
if selected=={'organisator'}:
    extra_excludes=['shared.apps.text','shared.apps.tools','shared.apps.communication','shared.apps.corrector','shared.apps.translator_chat','shared.apps.planner_agenda','shared.apps.sticky_wall','shared.apps.timer_widget','shared.apps.app_launcher']
if selected and selected <= {'dictionnator','explicator','tablinator'}:
    extra_excludes=['shared.apps.text','shared.apps.tools','shared.apps.communication','shared.apps.corrector','shared.apps.translator_chat','shared.apps.planner_agenda','shared.apps.sticky_wall','shared.apps.timer_widget','shared.apps.app_launcher','shared.apps.organizer_workspace','shared.apps.organizer_binder','shared.organizer','shared.documents']
a=Analysis([str(root/'run_satellite.py')],pathex=[str(root)],binaries=[],datas=[],
    hiddenimports=['pkgutil','unicodedata','binascii','textwrap','win32timezone','comtypes.gen.UIAutomationClient'],
    excludes=['PySide6.QtMultimedia','PySide6.QtMultimediaWidgets','llama_cpp','numpy','pytest','tkinter','PySide6.QtWebEngineCore','PySide6.QtWebEngineWidgets']+extra_excludes,noarchive=False)
pyz=PYZ(a.pure)
executables=[]
if selected and not selected <= set(APP_THEMES)-{'ergonatus','claviernator','precisionator','transcrinator','redactor','ecrinator','pdfinator'}:
    raise ValueError('ERGONATUS_BUILD_APP doit désigner un satellite compilable.')
for key,item in APP_THEMES.items():
    if key in ('ergonatus','claviernator','precisionator','transcrinator','redactor','ecrinator','pdfinator'):continue
    if selected and key not in selected:continue
    executables.append(EXE(pyz,a.scripts,[],exclude_binaries=True,name=item['folder'],debug=False,
        bootloader_ignore_signals=False,strip=False,upx=False,console=False,icon=str(root/'assets/orbs'/f'{key}.ico')))
coll=COLLECT(*executables,a.binaries,a.datas,strip=False,upx=False,name='ErgonatusSatellites')
