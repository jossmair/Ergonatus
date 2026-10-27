"""Publish only explicitly selected release files; never print credentials."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import hashlib
import base64
import urllib.parse
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parents[1]

def credentials():
    env = dict(os.environ, GIT_TERMINAL_PROMPT='0', GCM_INTERACTIVE='never')
    result = subprocess.run(['git', 'credential', 'fill'], input='protocol=https\nhost=github.com\n\n', text=True, capture_output=True, env=env, timeout=30)
    values = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
    token = values.get('password') or os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
    if not token:
        raise RuntimeError('Aucune authentification GitHub disponible via Git Credential Manager ou les variables GitHub.')
    return token

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('operation', choices=['inspect', 'publish'])
    args = parser.parse_args()
    token = credentials()
    def request(path, method='GET', payload=None, content_type='application/json'):
        data = None if payload is None else (json.dumps(payload).encode() if content_type == 'application/json' else payload)
        url = path if path.startswith('https://') else 'https://api.github.com' + path
        req = urllib.request.Request(url, data=data, method=method, headers={'Authorization': 'Bearer '+token, 'User-Agent': 'PDFinator-release', 'Accept': 'application/vnd.github+json', 'Content-Type': content_type, 'X-GitHub-Api-Version': '2022-11-28'})
        with urllib.request.urlopen(req, timeout=120) as response:
            return json.load(response)
    user = request('/user')
    if user['login'].lower() != 'jossmair':
        raise RuntimeError('Le compte GitHub connecté ne correspond pas au compte demandé.')
    repos = request('/user/repos?per_page=100&affiliation=owner')
    print(json.dumps({'account': user['login'], 'matching_repositories': [{'name': r['name'], 'private': r['private']} for r in repos if 'pdfinator' in r['name'].lower()]}, ensure_ascii=False))
    if args.operation == 'inspect':
        return
    verification = json.loads((ROOT / 'release-verification-100.json').read_text(encoding='utf-8'))
    assert verification['version'] == '1.0.0' and verification['tests_passed'] >= 156
    assert verification['strict_clippy'] and verification['real_pdf_tests_passed'] == 5
    assert verification['portable_verified'] and verification['installer_verified']
    files = [ROOT / 'dist' / name for name in [
        'PDFinator-1.0.0-portable-exe-windows-x64.zip',
        'PDFinator-1.0.0-Setup.exe', 'SHA256SUMS.txt']]
    for path in files:
        assert hashlib.sha256(path.read_bytes()).hexdigest() == verification['assets'][path.name]
    repo = 'jossmair/PDFinator'
    try:
        repository = request('/repos/' + repo)
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise
        repository = request('/user/repos', 'POST', {
            'name': 'PDFinator', 'description': 'Application Windows de lecture et modification de PDF, OCR local et export DOCX/ODT.',
            'private': False, 'has_issues': True, 'has_wiki': False, 'auto_init': False})
    if repository['owner']['login'].lower() != 'jossmair':
        raise RuntimeError('Propriétaire du dépôt incorrect.')
    public_files = {
        'README.md': (ROOT / 'release/README.md').read_text(encoding='utf-8'),
        'CHANGELOG.md': (ROOT / 'docs/RELEASE-1.0.0.md').read_text(encoding='utf-8'),
        'VALIDATION.md': (ROOT / 'release/VALIDATION.md').read_text(encoding='utf-8'),
    }
    for name, content in public_files.items():
        endpoint = '/repos/' + repo + '/contents/' + name
        payload = {'message': 'Publication PDFinator 1.0.0 : ' + name, 'content': base64.b64encode(content.encode()).decode()}
        try:
            existing = request(endpoint)
            if base64.b64decode(existing['content']).decode() == content:
                continue
            payload['sha'] = existing['sha']
        except urllib.error.HTTPError as exc:
            if exc.code != 404:
                raise
        request(endpoint, 'PUT', payload)
    try:
        release = request('/repos/' + repo + '/releases/tags/v1.0.0')
        if not release['draft']:
            raise RuntimeError('Une version publique v1.0.0 existe déjà : ne pas la remplacer automatiquement.')
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise
        branch = request('/repos/' + repo)['default_branch']
        notes = (ROOT / 'release/NOTES.md').read_text(encoding='utf-8').replace('/blob/main/', '/blob/' + urllib.parse.quote(branch, safe='') + '/')
        release = request('/repos/' + repo + '/releases', 'POST', {
            'tag_name': 'v1.0.0', 'name': 'PDFinator 1.0.0', 'draft': True, 'prerelease': False,
            'body': notes})
    endpoint = '/repos/' + repo + '/releases/' + str(release['id'])
    existing_assets = request(endpoint + '/assets')
    for path in files:
        existing = next((a for a in existing_assets if a['name'] == path.name), None)
        digest = 'sha256:' + verification['assets'][path.name]
        if existing:
            if existing.get('digest') != digest:
                raise RuntimeError('Une pièce jointe différente existe déjà dans le brouillon : ' + path.name)
            continue
        upload = release['upload_url'].split('{')[0] + '?name=' + urllib.parse.quote(path.name)
        assert urllib.parse.urlparse(upload).hostname == 'uploads.github.com'
        asset = request(upload, 'POST', path.read_bytes(), 'application/octet-stream')
        if asset.get('digest') != digest or asset['size'] != path.stat().st_size:
            raise RuntimeError('Contrôle du fichier téléversé échoué : ' + path.name)
    assets = request(endpoint + '/assets')
    assert {a['name'] for a in assets} == {p.name for p in files}
    for asset in assets:
        assert asset.get('digest') == 'sha256:' + verification['assets'][asset['name']]
    release = request(endpoint, 'PATCH', {'draft': False, 'make_latest': 'true'})
    published = request('/repos/' + repo + '/releases/tags/v1.0.0')
    assert not published['draft'] and len(published['assets']) == 3
    (ROOT / 'release/published.json').write_text(json.dumps({
        'repository': repository['html_url'], 'release': published['html_url'],
        'assets': [{'name': a['name'], 'url': a['browser_download_url'], 'sha256': a.get('digest')} for a in published['assets']]}, indent=2), encoding='utf-8')
    print(json.dumps({'published': published['html_url'], 'assets_verified': len(published['assets'])}))

if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(type(exc).__name__ + ': ' + str(exc))
        raise SystemExit(1)
