# CPU-only onedir distribution. Models are deliberately never embedded.
from pathlib import Path
import sys
from PyInstaller.utils.hooks import collect_dynamic_libs, collect_data_files

root = Path(SPECPATH)
datas = [(str(root / 'assets'), 'assets')]
datas += collect_data_files('llama_cpp')
binaries = collect_dynamic_libs('llama_cpp')
a = Analysis([str(root / 'main.py')], pathex=[str(root)], binaries=binaries, datas=datas,
    hiddenimports=['llama_cpp', 'jinja2.ext', 'comtypes.gen.UIAutomationClient', 'win32timezone',
                   'win32security', 'win32pipe', 'win32file', 'win32event', 'win32api', 'win32gui', 'win32process'],
    excludes=['tkinter', 'matplotlib', 'pandas', 'scipy', 'torch', 'tensorflow', 'PySide6.QtQml',
              'PySide6.QtQuick', 'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets'],
    noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='Redactor', debug=False,
    bootloader_ignore_signals=False, strip=False, upx=False, console=False,
    icon=str(root / 'assets' / 'redactor.ico'), manifest=str(root / 'assets' / 'redactor.manifest'))
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='Redactor-0.4.1')
