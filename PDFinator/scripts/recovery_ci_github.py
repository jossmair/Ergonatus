"""Bounded GitHub operations for the recovery/CI change; never print credentials."""
import argparse, json, urllib.request, urllib.error
from pathlib import Path
from github_release import credentials
ROOT=Path(__file__).resolve().parents[1]
PREFIX='/repos/jossmair/PDFinator'
token=credentials()
def api(path,method='GET',payload=None):
    req=urllib.request.Request('https://api.github.com'+path,method=method,
        data=None if payload is None else json.dumps(payload).encode(),
        headers={'Authorization':'Bearer '+token,'User-Agent':'PDFinator-CI-review','Accept':'application/vnd.github+json','Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=60) as response:return json.load(response)
parser=argparse.ArgumentParser();parser.add_argument('operation',choices=['create','status','log']);parser.add_argument('--job',type=int);args=parser.parse_args()
if args.operation=='create':
    existing=api(PREFIX+'/pulls?head=jossmair:improvements/recovery-ci&state=open')
    pr=existing[0] if existing else api(PREFIX+'/pulls','POST',{
        'title':'Récupérer les brouillons avec leur mise en forme et ajouter les contrôles CI',
        'head':'improvements/recovery-ci','base':'main','body':(ROOT/'release/recovery-ci-pr-body.md').read_text(encoding='utf-8')})
    (ROOT/'release/recovery-ci-pr.json').write_text(json.dumps({'number':pr['number'],'url':pr['html_url'],'head':pr['head']['sha']},indent=2),encoding='utf-8')
    print(json.dumps({'number':pr['number'],'url':pr['html_url'],'head':pr['head']['sha']}))
elif args.operation=='status':
    runs=api(PREFIX+'/actions/runs?branch=improvements%2Frecovery-ci&per_page=5')['workflow_runs']
    result=[]
    for run in runs:
        jobs=api(PREFIX+'/actions/runs/'+str(run['id'])+'/jobs')['jobs']
        result.append({'id':run['id'],'head':run['head_sha'],'event':run['event'],'status':run['status'],'conclusion':run['conclusion'],
            'url':run['html_url'],'jobs':[{'id':j['id'],'name':j['name'],'status':j['status'],'conclusion':j['conclusion'],
                'steps':[{'name':s['name'],'status':s['status'],'conclusion':s['conclusion']} for s in j.get('steps',[])]} for j in jobs]})
    (ROOT/'release/recovery-ci-status.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
else:
    assert args.job
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,req,fp,code,msg,headers,newurl):return None
    req=urllib.request.Request('https://api.github.com'+PREFIX+'/actions/jobs/'+str(args.job)+'/logs',headers={'Authorization':'Bearer '+token,'User-Agent':'PDFinator-CI-review'})
    try:
        response=urllib.request.build_opener(NoRedirect).open(req,timeout=60)
        body=response.read()
    except urllib.error.HTTPError as error:
        if error.code not in (301,302,303,307,308):raise
        url=error.headers['Location'];assert url.startswith('https://')
        # Do not forward the GitHub Authorization header to the log storage host.
        with urllib.request.urlopen(url,timeout=60) as response:body=response.read()
    path=ROOT/'release'/f'ci-job-{args.job}.log';path.write_bytes(body)
    lines=body.decode('utf-8-sig',errors='replace').splitlines()
    print('\n'.join(lines[-90:]))
