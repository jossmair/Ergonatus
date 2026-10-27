import os
from pathlib import Path
from fortinatus import __version__

# Keep unrelated native runtimes from developer tools out of the distribution.
os.environ['PATH'] = os.pathsep.join([
    str(Path(os.environ.get('SystemRoot', 'C:/Windows')) / 'System32'),
    os.environ.get('SystemRoot', 'C:/Windows'),
])

a = Analysis(['run_claviernator.py'], pathex=['.'], binaries=[],
             datas=[('assets/backgrounds', 'assets/backgrounds'),
                    ('assets/keyboard', 'assets/keyboard'),
                    ('assets/logo-clavier-v1.png', 'assets'),
                    ('assets/ajouter-touche-v1.png', 'assets')], hiddenimports=[],
             excludes=['PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'PySide6.QtTest',
                       'PySide6.QtPdf', 'PySide6.QtPdfWidgets', 'matplotlib', 'numpy', 'torch',
                       'tensorflow', 'tkinter', 'PIL', 'pytest', 'IPython', 'pyreadline3'],
             noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='Claviernator', debug=False,
          bootloader_ignore_signals=False, strip=False, upx=False, console=False,
          icon='assets/fortinatus.ico', version='assets/version_info.txt')
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name=f'Claviernator-{__version__}')

