"""Read the public GitHub release and hash downloads without authentication."""
from pathlib import Path
import hashlib, json, urllib.request

ROOT = Path(__file__).resolve().parents[1]
def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'PDFinator-public-verification'}), timeout=120)
with get('https://api.github.com/repos/jossmair/PDFinator/releases/tags/v1.0.0') as response:
    release = json.load(response)
assert not release['draft'] and not release['prerelease'] and release['tag_name'] == 'v1.0.0'
expected = json.loads((ROOT/'release-verification-100.json').read_text())['assets']
assert {a['name'] for a in release['assets']} == set(expected)
checked = []
for asset in release['assets']:
    url = asset['browser_download_url']
    assert url.startswith('https://github.com/jossmair/PDFinator/releases/download/v1.0.0/')
    hasher = hashlib.sha256()
    count = 0
    with get(url) as response:
        while chunk := response.read(1024*1024):
            hasher.update(chunk)
            count += len(chunk)
    assert hasher.hexdigest() == expected[asset['name']]
    assert count == asset['size']
    checked.append({'name': asset['name'], 'bytes': count, 'sha256': hasher.hexdigest()})
result = {'public_release': release['html_url'], 'authentication_used': False, 'downloaded_and_verified': checked}
(ROOT/'release/public-verification.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result, indent=2))
