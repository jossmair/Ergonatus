"""Attach verified, key-container-free sources while preserving released executables."""
from pathlib import Path
import json, hashlib, urllib.request, urllib.parse
from github_release import credentials
ROOT = Path(__file__).resolve().parents[1]
REPO = 'jossmair/PDFinator'
report = json.loads((ROOT/'release/source-verification.json').read_text())
assert report['clean_copy_tests_passed'] == 158 and report['key_containers_excluded']
token = credentials()
def api(path, method='GET', payload=None, binary=False):
    url = path if path.startswith('https://') else 'https://api.github.com'+path
    req = urllib.request.Request(url, data=payload if binary else (None if payload is None else json.dumps(payload).encode()), method=method,
        headers={'Authorization':'Bearer '+token,'User-Agent':'PDFinator-source-publication',
                 'Accept':'application/vnd.github+json','Content-Type':'application/octet-stream' if binary else 'application/json'})
    with urllib.request.urlopen(req, timeout=120) as response:
        return json.load(response)
assert api('/user')['login'].lower() == 'jossmair'
assert api('/repos/'+REPO+'/git/ref/heads/main')['object']['sha'] == report['source_commit']
tag = api('/repos/'+REPO+'/git/ref/tags/v1.0.0-sources')['object']
tag_target = api('/repos/'+REPO+'/git/tags/'+tag['sha'])['object']['sha'] if tag['type']=='tag' else tag['sha']
assert tag_target == report['source_commit']
release = api('/repos/'+REPO+'/releases/tags/v1.0.0')
original = {a['name']:a.get('digest') for a in release['assets']}
for name in ['PDFinator-1.0.0-sources.zip','PDFinator-1.0.0-sources.zip.sha256']:
    path = ROOT/'dist'/name
    digest = 'sha256:'+hashlib.sha256(path.read_bytes()).hexdigest()
    existing = next((a for a in release['assets'] if a['name']==name), None)
    if existing:
        assert existing.get('digest') == digest
        continue
    url = release['upload_url'].split('{')[0]+'?name='+urllib.parse.quote(name)
    assert urllib.parse.urlparse(url).hostname == 'uploads.github.com'
    asset = api(url,'POST',path.read_bytes(),binary=True)
    assert asset.get('digest') == digest and asset['size'] == path.stat().st_size
body = release['body']
marker = '<!-- PDFINATOR_SOURCES -->'
if marker not in body:
    body = f'''{marker}
### Code source disponible

[**Télécharger les sources complètes de la V1**](https://github.com/{REPO}/releases/download/v1.0.0/PDFinator-1.0.0-sources.zip) · [Parcourir le code](https://github.com/{REPO}/tree/v1.0.0-sources) · [Guide de compilation](https://github.com/{REPO}/blob/v1.0.0-sources/BUILDING.md)

Sources de l’application, dépendances locales, tests, ressources et licences inclus. La copie publiée a été compilée et ses 158 tests ont réussi. Les conteneurs de certificats et de clés de test amont sont exclus.

---

'''+body
api('/repos/'+REPO+'/releases/'+str(release['id']),'PATCH',{'body':body})
after = api('/repos/'+REPO+'/releases/tags/v1.0.0')
assert all(next(a for a in after['assets'] if a['name']==n).get('digest') == d for n,d in original.items())
result = {'repository':'https://github.com/'+REPO,'source_tag':'https://github.com/'+REPO+'/tree/v1.0.0-sources',
          'source_archive':'https://github.com/'+REPO+'/releases/download/v1.0.0/PDFinator-1.0.0-sources.zip',
          'source_commit':report['source_commit'],'original_assets_preserved':True}
(ROOT/'release/source-published.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
