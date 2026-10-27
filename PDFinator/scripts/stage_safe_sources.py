"""A fresh publication history excluding all certificate/key containers."""
from pathlib import Path
import subprocess, shutil, json, hashlib
ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT/'release/source-publication'
NEW = ROOT/'release/source-publication-safe'
assert (NEW/'.git').is_dir()
files = subprocess.check_output(['git','-C',str(OLD),'ls-files','-z']).decode().strip('\0').split('\0')
blocked = {'.p12','.pfx','.pem','.key','.jks','.keystore'}
selected, excluded = [], []
for name in files:
    path = OLD/name
    if path.suffix.lower() in blocked:
        excluded.append(name)
        continue
    target = NEW/name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, target)
    selected.append(name)
doc = NEW/'BUILDING.md'
text = doc.read_text(encoding='utf-8')
text += '\n## Données de test exclues\n\nLes conteneurs de certificats et de clés du jeu de tests amont (`.p12`, etc.)\nne sont pas distribués dans ce dépôt. Ils ne sont pas nécessaires pour compiler\nPDFinator ni pour exécuter sa suite de tests ; certains tests de signature du\nprojet fournisseur, exécutés séparément, demanderaient leurs propres fixtures.\n'
doc.write_bytes(text.encode('utf-8'))
readme = NEW/'README.md'
readme.write_bytes(readme.read_text(encoding='utf-8').encode())
expected = json.loads((ROOT/'release-verification-100.json').read_text())['sources']
for name,digest in expected.items():
    assert hashlib.sha256((NEW/name).read_bytes()).hexdigest() == digest
assert not [p for p in NEW.rglob('*') if p.is_file() and '.git' not in p.parts and p.suffix.lower() in blocked]
(ROOT/'release/source-safe-paths.txt').write_bytes(b''.join(n.encode()+b'\0' for n in selected))
(ROOT/'release/source-safe-staging.json').write_text(json.dumps({'files':len(selected),'excluded_key_containers':excluded,'application_sources_match_v1':True},indent=2),encoding='utf-8')
print(json.dumps({'files':len(selected),'excluded_key_containers':len(excluded),'application_sources_match_v1':True}))
