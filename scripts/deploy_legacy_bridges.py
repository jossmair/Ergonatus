"""Deploy rebuilt copies; keep the four previous distributions intact."""
from pathlib import Path
import shutil,json,hashlib,uuid
ROOT=Path(__file__).resolve().parents[1]
records=[]
original=ROOT/'docs/ASSEMBLY.json';backup=ROOT/'docs/ASSEMBLY-v01.json'
if not backup.exists():shutil.copy2(original,backup)
for name,version in [('Claviernator','1.3.10'),('Precisionator','1.0.7'),('Transcrinator','1.3.17'),('Redactor','0.4.1')]:
    base=ROOT/name;source=base/'.rebuilt'/(name+'-'+version)
    if not (source/(name+'.exe')).is_file():raise RuntimeError('Build absent : '+name)
    runtime=base/'runtime';archive=base/('runtime-before-bridge-'+uuid.uuid4().hex)
    if runtime.resolve().parent!=base.resolve() or archive.resolve().parent!=base.resolve():raise RuntimeError('Destination inattendue.')
    if runtime.exists():runtime.rename(archive)
    shutil.copytree(source,runtime)
    exe=runtime/(name+'.exe')
    records.append(dict(id=name.lower(),release=version,executable=str(exe.relative_to(ROOT)),sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),previous_runtime=str(archive.relative_to(ROOT)),change='Ergonatus Orb layout bridge, suite tray hidden, native interface preserved.'))
original.write_text(json.dumps(records,indent=2))
print('4 distributions adaptées installées ; anciennes copies archivées, originaux du workspace intacts.')
