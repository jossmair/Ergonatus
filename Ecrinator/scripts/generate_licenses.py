"""Generate audited offline redistribution notices from the actual normal Windows graph."""
from pathlib import Path
import hashlib,json,os,re,subprocess,sys,argparse
ROOT=Path(__file__).resolve().parents[1]
SUITE=ROOT.parent
sys.path.insert(0,str(SUITE/'PDFinator/scripts'))
# Import explicitly by path: this file has the same name as the sibling helper.
import importlib.util
spec=importlib.util.spec_from_file_location('pdfinator_legal_helper',SUITE/'PDFinator/scripts/generate_licenses.py')
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)

def build():
    env=os.environ.copy();tool=SUITE/'PDFinator/.tools'
    cargo=tool/'cargo/bin/cargo.exe'
    if cargo.is_file():env['CARGO_HOME']=str(tool/'cargo');env['RUSTUP_HOME']=str(tool/'rustup')
    else:cargo='cargo'
    meta=json.loads(subprocess.check_output([str(cargo),'metadata','--locked','--offline','--filter-platform','x86_64-pc-windows-msvc','--format-version','1'],cwd=ROOT,env=env))
    docs={};inventory=[]
    def add(label,path):
        text=Path(path).read_text(encoding='utf-8-sig').strip();key=hashlib.sha256(re.sub(r'\s+',' ',text).encode()).hexdigest()
        if not text:raise RuntimeError(f'Empty notice: {path}')
        entry=docs.setdefault(key,{'labels':[],'text':text});entry['labels'].append(label)
        return key
    for p in helper.normal_packages(meta):
        name=p['name'];label=f"{name} {p['version']}"
        if name=='ecrinator':paths=[ROOT/'licenses/LICENSE-MIT']
        elif name.startswith('wordcraft-'):paths=[ROOT/'vendor/wordcraft/LICENSE-MIT',ROOT/'vendor/wordcraft/NOTICE']
        elif name=='wuff':paths=[ROOT/'licenses/extra/wuff-MIT.txt']
        elif name=='krilla':paths=[ROOT/'licenses/extra/krilla-MIT.txt',ROOT/'licenses/extra/krilla-NOTICE.md']
        elif name in ['craft-pdf','craft-ui','craft-settings','craft-atomic','craft-quit']:
            parent=Path(p['manifest_path']).parent
            paths=next(([d/'LICENSE-MIT'] for d in [parent,*parent.parents] if (d/'LICENSE-MIT').is_file()),None)
            if paths is None:raise RuntimeError(f'Missing upstream MIT notice: {name}')
        else:paths=helper.licence_files(p)
        keys=[add(label,f) for f in paths]
        inventory.append({'name':name,'version':p['version'],'declared':p.get('license'),'notices':keys})
    add('Wordcraft — ressources et auteurs',ROOT/'vendor/wordcraft/ATTRIBUTION.md')
    add('Licence MPL 2.0 — fichiers concernés par les avis krilla',ROOT/'licenses/extra/MPL-2.0.txt')
    add('Licence Apache 2.0 — avis tiers',ROOT/'licenses/LICENSE-APACHE')
    for family in ['Borel','OpenDyslexic','NotoSerif']:add(f'Police {family}',ROOT/f'assets/fonts/{family}-OFL.txt')
    default_fonts=next(Path(p['manifest_path']).parent/'fonts' for p in meta['packages'] if p['name']=='epaint_default_fonts')
    for name in ['OFL.txt','UFL.txt','Hack-Regular.txt','emoji-icon-font-mit-license.txt']:add('Polices de l’interface egui',default_fonts/name)
    add('Ressources Écrinator',ROOT/'assets/ATTRIBUTION.md')
    add('Bibliothèque scolaire — crédits et licences par fichier',ROOT/'assets/library/ATTRIBUTION.md')
    for path in sorted((ROOT/'assets/library/licenses').rglob('*.txt')):add('Bibliothèque scolaire — licence historique '+path.stem,path)
    text='ÉCRINATOR — ERGONATUS\nMentions légales des composants redistribués.\n\n'
    text+='\n\n'.join('='*72+'\n'+', '.join(v['labels'])+'\n\n'+v['text'] for v in docs.values())+'\n'
    exe=ROOT/'runtime/Ecrinator.exe'
    report={'packages':inventory,'count':len(inventory),'cargo_lock_sha256':hashlib.sha256((ROOT/'Cargo.lock').read_bytes()).hexdigest(),'executable_sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),'notices_sha256':hashlib.sha256(text.encode()).hexdigest()}
    return text,report
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args()
    text,report=build();out=ROOT/'licenses/LICENCES.txt';inv=ROOT/'licenses/inventory.json'
    if args.check:
        assert out.read_text(encoding='utf-8')==text,'Regenerate notices for this build'
        assert json.loads(inv.read_text(encoding='utf-8'))==report,'Stale legal inventory'
    else:out.write_text(text,encoding='utf-8');inv.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f"{report['count']} composants, {len(text.encode())} octets de mentions légales.")
if __name__=='__main__':main()
