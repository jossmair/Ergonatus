"""Prepare a source-only checkout using an explicit allowlist, not workspace contents."""
from pathlib import Path
import hashlib, json, os, re, shutil
ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT/'release/source-publication'
assert (DEST/'.git').is_dir()
files = []
for directory in ['src','tests','examples','assets','licenses','vendor']:
    for base, dirs, names in os.walk(ROOT/directory):
        dirs[:] = [d for d in dirs if d not in {'.git','target','target-release','node_modules','__pycache__','.tools'}]
        for name in names:
            path = Path(base)/name
            if path.is_symlink() or name.endswith(('.log','.pyc')):
                continue
            files.append(path)
for name in ['Cargo.toml','Cargo.lock','build.rs','build.ps1']:
    files.append(ROOT/name)
for name in ['generate_licenses.py','package-portable.ps1','package-setup.ps1','pdfinator.iss',
             'verify_executable_icon.py','verify-shell-icon.ps1','verify_portable.py','verify-setup.ps1',
             'verify_independent.py','verify_oblique.py','verify_office.py','verify_percentages.py',
             'verify_prisms.py','verify_selection_regression.py','verify_worksheet.py',
             'verify_writer_regression.py','compare_office.py','verify_word.ps1']:
    files.append(ROOT/'scripts'/name)
patterns = [rb'gh[pousr]_[A-Za-z0-9]{25,}', rb'github_pat_[A-Za-z0-9_]{30,}',
            rb'AKIA[0-9A-Z]{16}', rb'-----BEGIN (?:OPENSSH |RSA |EC )?PRIVATE KEY-----',
            rb'C:[/\\]Users[/\\]Josselin', rb'C:/maths']
for path in files:
    rel = path.relative_to(ROOT)
    assert path.stat().st_size < 90*1024*1024
    if path.suffix.lower() in {'.rs','.py','.ps1','.toml','.md','.json','.txt','.yml','.yaml','.sh',''}:
        data = path.read_bytes()
        assert not any(re.search(p, data) for p in patterns), 'Review required: '+str(rel)
    target = DEST/rel
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, target)
expected = json.loads((ROOT/'release-verification-100.json').read_text())['sources']
for name, digest in expected.items():
    assert hashlib.sha256((DEST/name).read_bytes()).hexdigest() == digest, name
report = {'copied_files':len(files),'copied_bytes':sum(p.stat().st_size for p in files),
          'application_sources_match_v1':True,'private_workspace_directories_excluded':True,
          'text_secret_scan_passed':True,
          'copied_paths':[str(p.relative_to(ROOT)).replace('\\','/') for p in files]}
(ROOT/'release/source-staging.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='copied_paths'},indent=2))
