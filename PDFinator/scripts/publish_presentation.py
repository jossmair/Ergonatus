"""Publish the supplied screenshots and GitHub presentation in one commit."""
import base64
import hashlib
import json
from pathlib import Path
import urllib.request
from github_release import credentials

ROOT = Path(__file__).resolve().parents[1]
REPO = 'jossmair/PDFinator'
token = credentials()
def api(path, method='GET', payload=None):
    req = urllib.request.Request('https://api.github.com'+path,
        data=None if payload is None else json.dumps(payload).encode(), method=method,
        headers={'Authorization': 'Bearer '+token, 'User-Agent': 'PDFinator-presentation',
                 'Accept': 'application/vnd.github+json', 'Content-Type': 'application/json',
                 'X-GitHub-Api-Version': '2022-11-28'})
    with urllib.request.urlopen(req, timeout=120) as response:
        return json.load(response)

assert api('/user')['login'].lower() == 'jossmair'
repo = api('/repos/'+REPO)
branch = repo['default_branch']
head = api('/repos/'+REPO+'/git/ref/heads/'+branch)['object']['sha']
commit = api('/repos/'+REPO+'/git/commits/'+head)
release = api('/repos/'+REPO+'/releases/tags/v1.0.0')
original_assets = {a['name']: (a['id'], a.get('digest')) for a in release['assets']}
files = {'README.md': ROOT/'release/README.md'}
for name in ['banniere.svg','telecharger-installateur.svg','telecharger-portable.svg',
             'lecture.png','modifier.png','pages.png']:
    files['assets/'+name] = ROOT/'release/assets'/name
tree = []
for name, path in files.items():
    data = path.read_bytes()
    blob = api('/repos/'+REPO+'/git/blobs', 'POST',
               {'content': base64.b64encode(data).decode(), 'encoding': 'base64'})
    assert blob['sha'] == hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
    tree.append({'path': name, 'mode': '100644', 'type': 'blob', 'sha': blob['sha']})
new_tree = api('/repos/'+REPO+'/git/trees', 'POST', {'base_tree': commit['tree']['sha'], 'tree': tree})
new_commit = api('/repos/'+REPO+'/git/commits', 'POST', {
    'message': 'Présenter PDFinator : captures, fonctionnalités et téléchargements directs',
    'tree': new_tree['sha'], 'parents': [head]})
api('/repos/'+REPO+'/git/refs/heads/'+branch, 'PATCH', {'sha': new_commit['sha'], 'force': False})
raw = 'https://raw.githubusercontent.com/'+REPO+'/'+new_commit['sha']+'/assets/'
body = f'''<!-- PDFINATOR_SHOWCASE -->
<p align="center"><img src="{raw}banniere.svg" alt="PDFinator — Lisez. Modifiez. Organisez." width="100%"></p>

**Vos PDF, prêts à être retravaillés.** Corrigez un texte, annotez un cours et réorganisez vos pages, hors ligne et sans compte.

<p align="center">
<a href="https://github.com/{REPO}/releases/download/v1.0.0/PDFinator-1.0.0-Setup.exe"><img src="{raw}telecharger-installateur.svg" alt="Télécharger l’installeur Windows" width="310"></a>
<a href="https://github.com/{REPO}/releases/download/v1.0.0/PDFinator-1.0.0-portable-exe-windows-x64.zip"><img src="{raw}telecharger-portable.svg" alt="Télécharger le ZIP portable" width="310"></a>
</p>

### Modifiez directement sur la page
![Modification du texte et réglages de mise en forme]({raw}modifier.png)

### Lisez et annotez
![Lecture et navigation dans PDFinator]({raw}lecture.png)

### Réorganisez par glisser-déposer
![Déplacement d’une page et repère d’insertion]({raw}pages.png)

---

'''+(ROOT/'release/NOTES.md').read_text(encoding='utf-8')
api('/repos/'+REPO+'/releases/'+str(release['id']), 'PATCH', {'body': body})
api('/repos/'+REPO, 'PATCH', {
    'description': 'Vos PDF, prêts à être retravaillés. Lecture, modification, annotations, OCR local et export DOCX/ODT. Gratuit, hors ligne, sans compte. Windows x64.',
    'homepage': 'https://github.com/'+REPO+'/releases/latest'})
topics = sorted(set(repo.get('topics', [])) | {'pdf','pdf-editor','windows','ocr','docx','odt','portable','offline'})
api('/repos/'+REPO+'/topics', 'PUT', {'names': topics[:20]})
after = api('/repos/'+REPO+'/releases/tags/v1.0.0')
assert original_assets == {a['name']: (a['id'], a.get('digest')) for a in after['assets']}
assert api('/repos/'+REPO+'/git/ref/heads/'+branch)['object']['sha'] == new_commit['sha']
result = {'repository': repo['html_url'], 'release': after['html_url'], 'commit': new_commit['sha'],
          'published_files': list(files), 'release_assets_unchanged': True}
(ROOT/'release/presentation-published.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result, indent=2))
