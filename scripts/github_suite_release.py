"""Publish the reviewed suite, using Git Credential Manager without logging secrets."""
from pathlib import Path
import sys,os,json,subprocess,urllib.request,urllib.error,urllib.parse,hashlib,http.client
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/releases/2026.10.27';REPO='jossmair/Ergonatus';TAG='v2026.10.27'
def token():
    r=subprocess.run(['git','credential','fill'],input='protocol=https\nhost=github.com\n\n',text=True,capture_output=True,env=dict(os.environ,GIT_TERMINAL_PROMPT='0',GCM_INTERACTIVE='never'),timeout=30)
    values=dict(line.split('=',1) for line in r.stdout.splitlines() if '=' in line)
    value=values.get('password') or os.getenv('GH_TOKEN') or os.getenv('GITHUB_TOKEN')
    if not value:raise RuntimeError('Authentification GitHub indisponible.')
    return value
def api(path,method='GET',payload=None):
    req=urllib.request.Request('https://api.github.com'+path,data=None if payload is None else json.dumps(payload).encode(),method=method,headers={'Authorization':'Bearer '+TOKEN,'User-Agent':'Ergonatus-release','Accept':'application/vnd.github+json','Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=120) as r:return None if r.status==204 else json.load(r)
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
TOKEN=token();assert api('/user')['login'].lower()=='jossmair'
if sys.argv[1]=='create':
    try:r=api('/repos/'+REPO)
    except urllib.error.HTTPError as e:
        if e.code!=404:raise
        r=api('/user/repos','POST',dict(name='Ergonatus',description='Suite Windows locale : 21 outils pour apprendre, communiquer et organiser son quotidien.',private=False,auto_init=False,has_wiki=False))
    assert r['owner']['login'].lower()=='jossmair';print(r['html_url'])
elif sys.argv[1]=='tools':
    dest=OUT/'tools';dest.mkdir(parents=True,exist_ok=True)
    for name in ['7zr.exe','7z2605-extra.7z']:
        urllib.request.urlretrieve('https://github.com/ip7z/7zip/releases/download/26.05/'+name,dest/name)
    print('Outils 7-Zip officiels téléchargés.')
elif sys.argv[1] in ('stage','publish'):
    if sys.argv[1]=='publish':
        verification=json.loads((OUT/'verification.json').read_text());assert verification['portable_verified'] and verification['installer_verified']
    else:
        progress=json.loads((OUT/'verification-progress.json').read_text());assert progress['portable_verified']
        portable=sorted((OUT/'assets').glob('Ergonatus-2026.10.27-portable.zip.[0-9][0-9][0-9]'));assert len(portable)==5
        verification={'assets':{p.name:sha(p) for p in portable}}
    source=OUT/'source';head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()
    remote=api('/repos/'+REPO+'/git/ref/heads/main')['object']['sha'];assert remote==head
    candidates=[r for r in api('/repos/'+REPO+'/releases?per_page=100') if r['tag_name']==TAG]
    if candidates:
        assert all(r['draft'] for r in candidates),'Version déjà publique.'
        release=max(candidates,key=lambda r:sum(a['size'] for a in r['assets'] if a['state']=='uploaded'))
    else:
        release=api('/repos/'+REPO+'/releases','POST',dict(tag_name=TAG,target_commitish=head,name='Ergonatus — 27 octobre 2026',draft=True,prerelease=False,body=(OUT/'RELEASE-NOTES.md').read_text(encoding='utf-8')))
    existing=api('/repos/'+REPO+'/releases/'+str(release['id'])+'/assets')
    for name,digest in verification['assets'].items():
        p=OUT/'assets'/name;assert sha(p)==digest and p.stat().st_size<2*1024**3
        old=next((a for a in existing if a['name']==name),None)
        if old:assert old.get('digest')=='sha256:'+digest;continue
        url=urllib.parse.urlparse(release['upload_url'].split('{')[0]);assert url.hostname=='uploads.github.com'
        connection=http.client.HTTPSConnection(url.hostname,timeout=600)
        connection.putrequest('POST',url.path+'?name='+urllib.parse.quote(name));connection.putheader('Authorization','Bearer '+TOKEN);connection.putheader('User-Agent','Ergonatus-release');connection.putheader('Content-Type','application/octet-stream');connection.putheader('Content-Length',str(p.stat().st_size));connection.endheaders()
        sent=0;next_progress=256*1024**2
        with p.open('rb') as f:
            while block:=f.read(4*1024**2):
                connection.send(block);sent+=len(block)
                if sent>=next_progress:
                    print(name+' : '+str(round(sent/p.stat().st_size*100))+' %',flush=True);next_progress+=256*1024**2
        response=connection.getresponse();body=response.read();assert response.status==201,(response.status,body[:200]);asset=json.loads(body);connection.close()
        assert asset['size']==p.stat().st_size and asset.get('digest')=='sha256:'+digest
        print(name+' envoyé et vérifié.',flush=True)
    if sys.argv[1]=='publish':
        release=api('/repos/'+REPO+'/releases/'+str(release['id']),'PATCH',dict(draft=False,target_commitish=head))
        (OUT/'published.json').write_text(json.dumps(dict(url=release['html_url'],commit=head,assets=verification['assets']),indent=2));print(release['html_url'])
    else:print('Portable vérifié envoyé dans le brouillon ; publication finale en attente de la validation de installation.',flush=True)
