"""Smoke tests in new workspace folders; never installs into the user's account."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from zipfile import ZipFile
import pefile

root = Path(__file__).resolve().parents[1]
expected_catalog=json.loads((root/'assets/library/catalog.json').read_text(encoding='utf-8'))
expected_image_count=len(expected_catalog)
assert expected_image_count and not any(e['id'].startswith(('college-atlas-','college-om-')) for e in expected_catalog)
version = sys.argv[1] if len(sys.argv) > 1 else '0.9.0'
work = root / 'test-output' / ('distribution-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
work.mkdir(parents=True, exist_ok=False)
(work / 'tmp').mkdir()
env = os.environ.copy()
env.pop('ECRINATOR_DATA_DIR', None)
env.pop('ECRINATOR_QA_SCREENSHOT', None)
env['TEMP'] = env['TMP'] = str(work / 'tmp')
windows_root = os.environ.get('SystemRoot') or os.environ.get('WINDIR')
assert windows_root and Path(windows_root).is_dir(), 'Windows directory unavailable'
env['PATH'] = str(Path(windows_root) / 'System32') + os.pathsep + windows_root
startup = subprocess.STARTUPINFO()
startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
startup.wShowWindow = 0

def run(args):
    subprocess.run([str(a) for a in args], cwd=work, env=env, startupinfo=startup,
                   creationflags=subprocess.CREATE_NO_WINDOW, check=True, timeout=120)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

reference = root / 'runtime/Ecrinator.exe'
pe = pefile.PE(str(reference))
assert pe.FILE_HEADER.Machine == 0x8664, 'Expected a Windows x64 executable'
imports = sorted({e.dll.decode('ascii') for name in ['DIRECTORY_ENTRY_IMPORT', 'DIRECTORY_ENTRY_DELAY_IMPORT'] for e in getattr(pe, name, [])})
pe.close()
assert all(not any(x in name.lower() for x in ['python', 'vcruntime140', 'msvcp140']) for name in imports), imports

with ZipFile(root / f'dist/Ecrinator-{version}-portable-windows-x64.zip') as archive:
    assert set(archive.namelist()) == {f'Ecrinator/{n}' for n in ['Ecrinator.exe', 'LICENCES.txt', 'LIRE-MOI.txt', 'portable.flag']}
    archive.extractall(work / 'portable')
portable = work / 'portable/Ecrinator'
assert sha(portable / 'Ecrinator.exe') == sha(reference)
assert not (portable / 'library.eclib').exists(), 'Library must be embedded'
run([portable / 'Ecrinator.exe', '--verify', work / 'portable-documents'])
portable_report = json.loads((work / 'portable-documents/verification.json').read_text())
assert portable_report['native_roundtrip'] and portable_report['pages'] >= 3
assert portable_report['library_images']==expected_image_count
assert (portable / 'data/diagnostic.log').is_file(), 'portable data directory was not used'

# Prove that copying only the executable still provides every image and thumbnail.
standalone=work/'standalone';standalone.mkdir()
import shutil
shutil.copyfile(reference,standalone/'Ecrinator.exe')
env['ECRINATOR_DATA_DIR']=str(work/'standalone-data')
run([standalone/'Ecrinator.exe','--verify',work/'standalone-documents'])
standalone_report=json.loads((work/'standalone-documents/verification.json').read_text())
assert standalone_report['library_images']==expected_image_count
assert list(standalone.iterdir())==[standalone/'Ecrinator.exe']
env.pop('ECRINATOR_DATA_DIR',None)

installed = work / 'installer-extraction'
run([root / f'dist/Ecrinator-{version}-Setup.exe', '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-',
     f'/DIR={installed}', '/TESTINSTALL=1', f'/LOG={work / "installer.log"}'])
deadline = time.monotonic() + 45
while time.monotonic() < deadline:
    log = (work / 'installer.log').read_text(encoding='utf-8-sig', errors='replace') if (work / 'installer.log').exists() else ''
    if 'Log closed.' in log:
        break
    time.sleep(0.2)
assert 'Installation process succeeded.' in log and 'Log closed.' in log, 'Installer did not complete successfully'
assert sha(installed / 'Ecrinator.exe') == sha(reference)
assert not (installed/'library.eclib').exists(), 'Installed app must need no sidecar'
assert (installed / 'LICENCES.txt').is_file()
assert not (installed / 'portable.flag').exists()
env['ECRINATOR_DATA_DIR'] = str(work / 'installed-data')
run([installed / 'Ecrinator.exe', '--verify', work / 'installed-documents'])
installed_report = json.loads((work / 'installed-documents/verification.json').read_text())
assert installed_report['native_roundtrip'] and installed_report['recovery_roundtrip']
assert installed_report['library_images']==expected_image_count
assert installed.resolve().is_relative_to((root / 'test-output').resolve())
run([installed / 'unins000.exe', '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', f'/LOG={work / "uninstaller.log"}'])
deadline = time.monotonic() + 45
while (installed / 'Ecrinator.exe').exists() and time.monotonic() < deadline:
    time.sleep(0.2)
assert not (installed / 'Ecrinator.exe').exists(), 'Smoke uninstaller left the application executable'
assert not (installed/'library.eclib').exists(), 'Smoke uninstaller left the installed library'
assert (work / 'installed-documents/Cours de mathématiques.ecr').is_file(), 'Uninstall removed a course'
assert (work / 'installed-data/diagnostic.log').is_file(), 'Uninstall removed application data'

with ZipFile(root / f'dist/Ecrinator-{version}-icones-et-illustration.zip') as archive:
    assert sum(n.startswith('icones/') and n.endswith('.svg') for n in archive.namelist()) == 92
    assert sum(n.startswith('bandeaux/') and n.endswith('.png') for n in archive.namelist()) == 13
    assert 'fond/workspace-banner-v1.png' in archive.namelist()
    assert 'fond/workspace-banner-v1.PROMPT.json' in archive.namelist()
    assert 'fond/workspace-banner-v2.png' in archive.namelist()
    assert 'fond/workspace-banner-v2.PROMPT.json' in archive.namelist()
    assert 'fond/workspace-banner-v3.png' in archive.namelist()
    assert 'fond/workspace-banner-v3.PROMPT.json' in archive.namelist()
    assert sum(n.startswith('fonds-matieres/') and n.endswith('.png') for n in archive.namelist()) == 13
    assert archive.testzip() is None

with ZipFile(root / f'dist/Ecrinator-{version}-fonds-matieres.zip') as archive:
    pngs = [n for n in archive.namelist() if n.endswith('.png')]
    assert len(pngs) == 13
    assert len({hashlib.sha256(archive.read(n)).hexdigest() for n in pngs}) == 13
    assert archive.testzip() is None
    assert len(json.loads(archive.read('PROMPTS.json'))) == 13

with ZipFile(root/f'dist/Ecrinator-{version}-bibliotheque-scolaire.zip') as archive:
    assert archive.testzip() is None
    catalog=json.loads(archive.read('catalog.json'))
    assert len(catalog)==expected_image_count and {e['id'] for e in catalog}=={e['id'] for e in expected_catalog}
    for e in catalog:assert hashlib.sha256(archive.read(e['filename'])).hexdigest()==e['sha256']

result = {'version': version, 'date_local': datetime.now().isoformat(timespec='seconds'), 'offline_library_images':len(catalog),
          'executable_sha256': sha(reference), 'pe_imports': imports,
          'standalone_executable_library_verified':True,'standalone_report':standalone_report,
          'portable_archive_whitelist': True, 'portable_data_is_local': True,
          'portable_self_verification': portable_report, 'installer_smoke_mode': True,
          'installer_executable_identical': True, 'installed_self_verification': installed_report,
          'smoke_uninstall_removed_executable': True, 'smoke_uninstall_preserved_documents_and_data': True,
          'child_path_only_windows': True, 'icon_pack_svg_count': 92, 'subject_illustrations':13,
          'workspace_background_and_prompt_in_assets':True, 'distinct_subject_background_sources':13,
          'clean_windows_without_python_tested': False, 'real_user_install_uninstall_tested': False,
          'workspace_test_folder': str(work)}
(root / 'test-output/distribution-verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(result, ensure_ascii=False, indent=2))
