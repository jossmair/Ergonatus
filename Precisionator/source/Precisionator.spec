# Build from the project folder with Python 3.12 x64.
from pathlib import Path
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

os.environ['PATH'] = os.pathsep.join([
    str(Path(os.environ.get('SystemRoot', 'C:/Windows')) / 'System32'),
    os.environ.get('SystemRoot', 'C:/Windows'),
])

a = Analysis(['main.py'], pathex=['.'], binaries=[],
    datas=[('assets', 'assets')] + collect_data_files('dxcam'),
    hiddenimports=collect_submodules('dxcam') + ['comtypes.stream'],
    excludes=['PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets',
              'PySide6.QtPdf', 'PySide6.QtPdfWidgets', 'PySide6.QtTest',
              'matplotlib', 'torch', 'tensorflow', 'tkinter', 'PIL', 'pytest', 'IPython'],
    noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='Precisionator',
    debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
    console=False, icon='assets/precisionator.ico',
    version='assets/version_info.txt', manifest='assets/precisionator.manifest')
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='Precisionator-1.0.7')
