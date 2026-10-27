from pathlib import Path
from PyInstaller.utils.hooks import collect_dynamic_libs,collect_data_files
root=Path(SPECPATH).parent
a=Analysis([str(root/'run_translation.py')],pathex=[str(root),str(root/'Redactor/source')],
    binaries=collect_dynamic_libs('llama_cpp'),datas=collect_data_files('llama_cpp'),hiddenimports=['app.ai.engine','jinja2.ext'],
    excludes=['PySide6','pytest','tkinter'],noarchive=False)
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,[],exclude_binaries=True,name='ErgoTranslate',debug=False,strip=False,upx=False,console=False)
coll=COLLECT(exe,a.binaries,a.datas,strip=False,upx=False,name='ErgoTranslate')
