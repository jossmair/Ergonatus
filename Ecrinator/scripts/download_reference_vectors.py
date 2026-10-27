from pathlib import Path
import requests,json,base64,time
ROOT=Path(__file__).resolve().parents[1];out=ROOT/'test-output/reference-sources';s=requests.Session();s.headers['User-Agent']='Ecrinator curriculum reference curation'
urls={
'bioicons-tree.json':'https://api.github.com/repos/duerrsimon/bioicons/git/trees/master?recursive=1',
'bioicons-repo.json':'https://api.github.com/repos/duerrsimon/bioicons',
'history-license-change.json':'https://api.github.com/repos/openstax/osbooks-world-history/commits/b2ddac6d5ab41847257c1484ee9271576d1a053e',
'siyavula-org-page2.json':'https://api.github.com/orgs/Siyavula/repos?per_page=100&page=2',
'siyavula-nst9.json':'https://api.github.com/repos/Siyavula/NST-Grade-9-Workbook',
}
for name,url in urls.items():
 try:
  p=out/name
  if not p.exists():r=s.get(url,timeout=60);r.raise_for_status();p.write_bytes(r.content)
  print(name,p.stat().st_size,flush=True)
 except Exception as e:print('UNAVAILABLE',name,str(e),flush=True)
p=out/'history-license-change.json'
if p.exists():
 meta=json.loads(p.read_text(encoding='utf-8'));sha=meta['parents'][0]['sha'];license=s.get(f'https://raw.githubusercontent.com/openstax/osbooks-world-history/{sha}/LICENSE',timeout=60);license.raise_for_status();text=license.text
 print('HISTORY SNAPSHOT',sha,text[:70],flush=True)
 if 'Attribution 4.0 International'in text[:200]:
  (out/'history-CC-BY4-LICENSE.txt').write_text(text,encoding='utf-8');(out/'history-CC-BY4-snapshot.json').write_text(json.dumps({'sha':sha,'license_url':f'https://github.com/openstax/osbooks-world-history/blob/{sha}/LICENSE','date':meta['commit']['committer']['date']},indent=2),encoding='utf-8')
  archive=out/'openstax-world-history-CC-BY4.zip'
  if not archive.exists():r=s.get(f'https://codeload.github.com/openstax/osbooks-world-history/zip/{sha}',timeout=240);r.raise_for_status();archive.write_bytes(r.content)
  print('HISTORY ARCHIVE',archive.stat().st_size,flush=True)
