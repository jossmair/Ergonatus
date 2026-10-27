"""Publish verified 1.0.1 assets without changing historical releases."""
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
HEAD = '54e5dc1e9d5d7854a3a6de621f431cee8455037a'
NAMES = ['PDFinator-1.0.1-portable-exe-windows-x64.zip', 'PDFinator-1.0.1-Setup.exe']
EXPECTED = ['84a8642e4b27769df7fffac58b61000a4d08710dea68f6781040e541ad92a73e',
            '092c52523889d0672db9b867a541feb22debf1c8940da071e127af510a5f792a']
sha = lambda data: hashlib.sha256(data).hexdigest()

def validate():
    assert subprocess.check_output(['git', 'rev-parse', HEAD], cwd=SOURCE, text=True).strip() == HEAD
    tests = (ROOT/'release/test-101-final.log').read_text(errors='replace')
    assert sum(map(int, re.findall(r'test result: ok\. (\d+) passed;', tests))) == 167
    assert 'test result: FAILED' not in tests
    assert 'Finished `dev` profile' in (ROOT/'release/clippy-101.log').read_text(errors='replace')
    assert (SOURCE/'setup-verification-101.json').is_file()
    setup = json.loads((SOURCE/'setup-verification-101.json').read_text())
    assert setup['Version'] == '1.0.1' and all(setup[k] for k in ['PayloadHashesMatch','Uninstalled','TestDirectoryRemoved'])
    portable = json.loads((SOURCE/'portable-exe-verification-101.json').read_text())
    assert portable['version'] == '1.0.1' and all(portable[k] for k in ['crc_valid','payload_matches','icon_verified'])
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
        print('1.0.1: 167 tests, package payloads and installation checks validated.'); return
    token=credentials()
    def api(path,method='GET',payload=None,ctype='application/json'):
        url=path if path.startswith('https://') else 'https://api.github.com'+path
        assert url.startswith(('https://api.github.com/','https://uploads.github.com/'))
        body=None if payload is None else (json.dumps(payload).encode() if ctype=='application/json' else payload)
        req=urllib.request.Request(url,data=body,method=method,headers={'Authorization':'Bearer '+token,
            'User-Agent':'PDFinator-1.0.1-release','Accept':'application/vnd.github+json','Content-Type':ctype})
        with urllib.request.urlopen(req,timeout=180) as r:return json.load(r)
    if args.operation=='publish':
        pr=api(PREFIX+'/pulls/1')
        assert pr['merged'] and pr['head']['sha']==HEAD
        commit=pr['merge_commit_sha']
        assert api(PREFIX+'/git/ref/heads/main')['object']['sha']==commit
        runs=api(PREFIX+'/actions/runs?head_sha='+HEAD+'&event=pull_request')['workflow_runs']
        passed=[r for r in runs if r['conclusion']=='success' and r['head_sha']==HEAD]
        assert passed, 'Exact final source revision must pass GitHub CI'
        jobs=api(PREFIX+'/actions/runs/'+str(passed[0]['id'])+'/jobs')['jobs']
        assert len(jobs)==2 and all(j['conclusion']=='success' for j in jobs)
        try: ref=api(PREFIX+'/git/ref/tags/v1.0.1')
        except urllib.error.HTTPError as e:
            if e.code!=404:raise
            ref=api(PREFIX+'/git/refs','POST',{'ref':'refs/tags/v1.0.1','sha':commit})
        assert ref['object']['sha']==commit, 'Never move an existing tag'
        releases=api(PREFIX+'/releases?per_page=100')
        release=next((r for r in releases if r['tag_name']=='v1.0.1'),None)
        if release is None:
            release=api(PREFIX+'/releases','POST',{'tag_name':'v1.0.1','target_commitish':commit,
                'name':'PDFinator 1.0.1 — retrouvez vos brouillons','body':(ROOT/'release/recovery-101-notes.md').read_text(encoding='utf-8'),
                'draft':True,'prerelease':False})
        assert release['draft'], 'Already published: use verify instead'
        for name in names:
            data=(SOURCE/'dist'/name).read_bytes()
            asset=next((a for a in release['assets'] if a['name']==name),None)
            if asset is None:
                asset=api(release['upload_url'].split('{')[0]+'?name='+name,'POST',data,'application/octet-stream')
            assert asset['size']==len(data) and asset.get('digest')=='sha256:'+sha(data)
        release=api(PREFIX+'/releases/'+str(release['id']),'PATCH',{'draft':False,'make_latest':'true'})
        (ROOT/'release/published-101.json').write_text(json.dumps({'url':release['html_url'],'source_commit':commit,
            'ci_head':HEAD,'ci_run':passed[0]['id'],'assets':{n:sha((SOURCE/'dist'/n).read_bytes()) for n in names}},indent=2))
        print(release['html_url'])
    else:
        # Public downloads carry no credential headers, including through redirects.
        release=api(PREFIX+'/releases/tags/v1.0.1')
        assert not release['draft']
        record=json.loads((ROOT/'release/published-101.json').read_text())
        assert api(PREFIX+'/git/ref/tags/v1.0.1')['object']['sha']==record['source_commit']
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
        print('1.0.1 source tag and unchanged historical 1.0.0 assets verified')

if __name__=='__main__':main()
