"""Publish verified 1.0.2 assets without changing historical releases."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import urllib.error
import urllib.request
import zipfile
from github_release import credentials

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'release/source-publication-safe'
PREFIX = '/repos/jossmair/PDFinator'
HEAD = '4ddd03e279c19d80dcf58fe11faac28d34973606'
NAMES = ['PDFinator-1.0.2-portable-exe-windows-x64.zip', 'PDFinator-1.0.2-Setup.exe']
EXPECTED = ['161e3b18e10b89cc2f510921b3bc44b64fbe9b6dbf86c64411aaafbfb6c1f23d',
            'bec7ffa5d8ea1d92ad7f9340bd86164840865983058a2ad972177866606967ad']
sha = lambda data: hashlib.sha256(data).hexdigest()

def validate():
    assert subprocess.check_output(['git', 'rev-parse', HEAD], cwd=SOURCE, text=True).strip() == HEAD
    tests = (ROOT/'release/office-full-tests.log').read_text(errors='replace')
    assert sum(map(int, re.findall(r'test result: ok\. (\d+) passed;', tests))) == 168
    assert 'test result: FAILED' not in tests
    assert 'Finished `dev` profile' in (ROOT/'release/office-clippy.log').read_text(errors='replace')
    corpus = json.loads((SOURCE/'test-output/office-corpus/verification.json').read_text())
    assert len(corpus) == 2 and all(r['script_size_preserved'] and r['mixed_pages'] == 3 for r in corpus)
    worksheet = json.loads((SOURCE/'test-output/office-final-worksheet.json').read_text())
    prisms = json.loads((SOURCE/'test-output/office-final-prisms.json').read_text())
    percentages = json.loads((SOURCE/'test-output/47-verification.json').read_text())['results']
    assert len(worksheet) == len(prisms) == len(percentages) == 2
    assert all(r['pages'] == 1 and r['checked_tokens'] == 367 for r in worksheet)
    assert all(r['pages'] == 1 and r['tokens'] == 54 for r in prisms)
    assert all(r['pages'] == 1 and r['editable_fractions'] == 5 for r in percentages)
    assert (SOURCE/'setup-verification-102.json').is_file()
    setup = json.loads((SOURCE/'setup-verification-102.json').read_text())
    assert setup['Version'] == '1.0.2' and all(setup[k] for k in ['PayloadHashesMatch','Uninstalled','TestDirectoryRemoved'])
    portable = json.loads((SOURCE/'portable-exe-verification-102.json').read_text())
    assert portable['version'] == '1.0.2' and all(portable[k] for k in ['crc_valid','payload_matches','icon_verified'])
    with zipfile.ZipFile(SOURCE/'dist'/NAMES[0]) as z:
        assert z.testzip() is None
        assert z.read('PDFinator/PDFinator.exe') == (SOURCE/'runtime/pdfinator.exe').read_bytes()
        assert z.read('PDFinator/LICENCES.txt') == (SOURCE/'licenses/LICENCES.txt').read_bytes()
    for name, digest in zip(NAMES, EXPECTED):
        assert sha((SOURCE/'dist'/name).read_bytes()) == digest
    sums = ''.join(f'{digest}  {name}\n' for name,digest in zip(NAMES,EXPECTED))
    (SOURCE/'dist/SHA256SUMS.txt').write_bytes(sums.encode())
    return NAMES + ['SHA256SUMS.txt']

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('operation',choices=['validate','publish','verify']); args=parser.parse_args()
    names=validate()
    if args.operation=='validate':
        print('1.0.2: 168 tests, package payloads and installation checks validated.'); return
    token=credentials()
    def api(path,method='GET',payload=None,ctype='application/json'):
        url=path if path.startswith('https://') else 'https://api.github.com'+path
        assert url.startswith(('https://api.github.com/','https://uploads.github.com/'))
        body=None if payload is None else (json.dumps(payload).encode() if ctype=='application/json' else payload)
        req=urllib.request.Request(url,data=body,method=method,headers={'Authorization':'Bearer '+token,
            'User-Agent':'PDFinator-1.0.2-release','Accept':'application/vnd.github+json','Content-Type':ctype})
        with urllib.request.urlopen(req,timeout=180) as r:return json.load(r)
    if args.operation=='publish':
        pr=api(PREFIX+'/pulls/4')
        assert pr['merged'] and pr['head']['sha']==HEAD
        commit=pr['merge_commit_sha']
        assert api(PREFIX+'/git/ref/heads/main')['object']['sha']==commit
        assert api(PREFIX+'/git/commits/'+commit)['tree']['sha']==api(PREFIX+'/git/commits/'+HEAD)['tree']['sha'], 'Merged source must match the tested and built tree'
        runs=api(PREFIX+'/actions/runs?head_sha='+HEAD+'&event=pull_request')['workflow_runs']
        passed=[r for r in runs if r['conclusion']=='success' and r['head_sha']==HEAD]
        assert passed, 'Exact final source revision must pass GitHub CI'
        jobs=api(PREFIX+'/actions/runs/'+str(passed[0]['id'])+'/jobs')['jobs']
        assert len(jobs)==2 and all(j['conclusion']=='success' for j in jobs)
        try: ref=api(PREFIX+'/git/ref/tags/v1.0.2')
        except urllib.error.HTTPError as e:
            if e.code!=404:raise
            ref=api(PREFIX+'/git/refs','POST',{'ref':'refs/tags/v1.0.2','sha':commit})
        assert ref['object']['sha']==commit, 'Never move an existing tag'
        releases=api(PREFIX+'/releases?per_page=100')
        release=next((r for r in releases if r['tag_name']=='v1.0.2'),None)
        if release is None:
            release=api(PREFIX+'/releases','POST',{'tag_name':'v1.0.2','target_commitish':commit,
                'name':'PDFinator 1.0.2 — indices et exposants plus fidèles','body':(ROOT/'release/office-102-notes.md').read_text(encoding='utf-8'),
                'draft':True,'prerelease':False})
        assert release['draft'], 'Already published: use verify instead'
        for name in names:
            data=(SOURCE/'dist'/name).read_bytes()
            asset=next((a for a in release['assets'] if a['name']==name),None)
            if asset is None:
                asset=api(release['upload_url'].split('{')[0]+'?name='+name,'POST',data,'application/octet-stream')
            assert asset['size']==len(data) and asset.get('digest')=='sha256:'+sha(data)
        release=api(PREFIX+'/releases/'+str(release['id']),'PATCH',{'draft':False,'make_latest':'true'})
        (ROOT/'release/published-102.json').write_text(json.dumps({'url':release['html_url'],'source_commit':commit,
            'ci_head':HEAD,'ci_run':passed[0]['id'],'assets':{n:sha((SOURCE/'dist'/n).read_bytes()) for n in names}},indent=2))
        print(release['html_url'])
    else:
        # Public downloads carry no credential headers, including through redirects.
        release=api(PREFIX+'/releases/tags/v1.0.2')
        assert not release['draft']
        record=json.loads((ROOT/'release/published-102.json').read_text())
        assert api(PREFIX+'/git/ref/tags/v1.0.2')['object']['sha']==record['source_commit']
        historical=api(PREFIX+'/git/ref/tags/v1.0.0-sources')['object']
        if historical['type']=='tag':
            historical=api(PREFIX+'/git/tags/'+historical['sha'])['object']
        assert historical['sha']=='11632ae4cb33a90b6ce6aca832a4244cff043e02'
        old=api(PREFIX+'/releases/tags/v1.0.0')
        for name,digest in [('PDFinator-1.0.0-portable-exe-windows-x64.zip','11b353849945ed20bdf4e36ca422361f20270893af57333d13b38fb145409572'),
                            ('PDFinator-1.0.0-Setup.exe','10979fe5b79709d3d1e1134c4cdf2f3d62fa49dfb8fa61120c872079ca612357')]:
            assert next(a for a in old['assets'] if a['name']==name)['digest']=='sha256:'+digest
        for name in names:
            url=next(a['browser_download_url'] for a in release['assets'] if a['name']==name)
            with urllib.request.urlopen(url,timeout=180) as r: data=r.read()
            assert sha(data)==sha((SOURCE/'dist'/name).read_bytes()),name
            print(name+': public download SHA-256 verified')
        print('1.0.2 source tag and unchanged historical 1.0.0 assets verified')

if __name__=='__main__':main()
