"""Bind the verified sources, checks and exact binaries before GitHub publication."""
from pathlib import Path
import hashlib, json, re

ROOT = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
tests = (ROOT/'test-100-publish.log').read_text(encoding='utf-8-sig')
counts = [int(x) for x in re.findall(r'test result: ok\. (\d+) passed;', tests)]
assert len(counts) == 10 and sum(counts) == 158 and 'FAILED' not in tests
clippy = (ROOT/'clippy-100-publish.log').read_text(encoding='utf-8-sig')
assert 'Finished `dev`' in clippy and 'error:' not in clippy
office = (ROOT/'test-office-100.log').read_text(encoding='utf-8-sig')
assert '5 passed; 0 failed' in office
recovery = (ROOT/'recovery-100.log').read_text(encoding='utf-8-sig')
assert 'WRITE_EXIT=77' in recovery and 'RECOVERY_VERIFIED:' in recovery
mixed = (ROOT/'mixed-ocr-100.log').read_text(encoding='utf-8-sig')
assert '1 passed; 0 failed' in mixed
comparisons = json.loads((ROOT/'audit/v1-1.0.0/export-comparisons.json').read_text(encoding='utf-8'))
assert len(comparisons) == 3 and all(v['passed'] for v in comparisons.values())
portable = json.loads((ROOT/'portable-exe-verification-100.json').read_text(encoding='utf-8-sig'))
setup = json.loads((ROOT/'setup-verification-100.json').read_text(encoding='utf-8-sig'))
assert portable['version'] == setup['Version'] == '1.0.0'
assert portable['crc_valid'] and portable['payload_matches'] and portable['icon_verified']
assert setup['PayloadHashesMatch'] and setup['Uninstalled'] and setup['TestDirectoryRemoved']
assert sha(ROOT/'runtime/pdfinator.exe') == sha(ROOT/'target-release/release/pdfinator.exe') == portable['executable_sha256']
assets = [ROOT/'dist/PDFinator-1.0.0-portable-exe-windows-x64.zip', ROOT/'dist/PDFinator-1.0.0-Setup.exe']
assert sha(assets[0]) == portable['sha256']
assert sha(assets[1]) == setup['SetupSHA256'].lower()
sums = ROOT/'dist/SHA256SUMS.txt'
sums.write_text(''.join(f'{sha(p)}  {p.name}\n' for p in assets), encoding='utf-8')
assets.append(sums)
source_paths = sorted((ROOT/'src').rglob('*.rs')) + [ROOT/'Cargo.toml', ROOT/'Cargo.lock', ROOT/'build.rs', ROOT/'assets/pdfinator.ico']
result = {
    'version': '1.0.0', 'tests_passed': sum(counts), 'suite_counts': counts,
    'strict_clippy': True, 'real_pdf_tests_passed': 5,
    'office_render_comparisons': 6, 'real_mixed_ocr': True, 'cross_process_recovery': True,
    'portable_verified': True, 'installer_verified': True,
    'physical_printing_tested': False, 'full_native_ui_validation': False,
    'authenticode_signed': False,
    'executable_sha256': portable['executable_sha256'],
    'assets': {p.name: sha(p) for p in assets},
    'sources': {str(p.relative_to(ROOT)).replace('\\','/'): sha(p) for p in source_paths},
}
(ROOT/'release-verification-100.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps({k: v for k, v in result.items() if k != 'sources'}, indent=2))
