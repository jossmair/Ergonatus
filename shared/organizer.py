"""Offline, bounded classification and journalled, non-overwriting Windows moves."""
from pathlib import Path
from dataclasses import dataclass
import os, re, json, stat, time, uuid, hashlib, unicodedata, zipfile, threading
import xml.etree.ElementTree as ET

INBOX='À classer'
DOCUMENT_LOCK=threading.RLock()
PROFILES={
    'École primaire':['Français','Mathématiques','Questionner le monde','Histoire-géographie','Sciences','Langues','Arts plastiques','Musique','EPS','Documents école','Projets',INBOX],
    'Collège':['Français','Mathématiques','Histoire-géographie','EMC','Anglais','Langues','SVT','Physique-chimie','Technologie','EPS','Arts plastiques','Musique','Orientation','Documents école',INBOX],
    'Professionnel':['Factures','Devis','Contrats','Clients','Projets','Réunions','Ressources humaines','Administratif','Images','Archives',INBOX],
    'Particulier':['Administratif','Factures','Impôts','Banque','Santé','Logement','Véhicule','Assurances','Photos','Vidéos','Musique','Projets',INBOX],
}
SCHOOL={'École primaire','Collège'}
COLORS=['#E49B91','#85B7E9','#D9AF69','#C4A0E1','#82C8B8','#E8AC7A','#A7B8D8','#97C892','#D6A2C1','#D0C27A','#81C8D2','#B5A0D4','#88BD72','#D6AEAC','#CAB379']
KEYWORDS={
    'Français':['francais','grammaire','conjugaison','orthographe','lecture','dictee','poesie','litterature'],
    'Mathématiques':['mathematiques','maths','mathematique','fractions','geometrie','equations','calcul','algebre'],
    'Questionner le monde':['questionner le monde','decouverte du monde','vivant','espace temps'],
    'Histoire-géographie':['histoire','geographie','geo','antiquite','revolution','guerre mondiale','cartographie'],
    'Sciences':['sciences','scientifique','experience','biologie','electricite'],
    'EMC':['emc','enseignement moral','citoyennete','laicite'],
    'Anglais':['anglais','english','vocabulary','grammar'],
    'Langues':['anglais','english','espagnol','allemand','italien','latin','grec','vocabulaire'],
    'SVT':['svt','sciences de la vie','biologie','geologie','cellule','ecosysteme'],
    'Physique-chimie':['physique','chimie','molecule','electricite','atome'],
    'Technologie':['technologie','programmation','robotique','scratch'],
    'EPS':['eps','sport','athletisme','natation','gymnastique'],
    'Arts plastiques':['arts plastiques','dessin','peinture','arts visuels'],
    'Musique':['musique','partition','solfege','education musicale'],
    'Orientation':['orientation','parcours avenir','stage troisieme','metiers'],
    'Documents école':['bulletin','certificat scolaire','inscription scolaire','conseil de classe','cantine'],
    'Factures':['facture','invoice','ticket de caisse','recu de paiement'],
    'Devis':['devis','quotation','proposition commerciale'],
    'Contrats':['contrat','convention','accord de confidentialite','conditions contractuelles'],
    'Clients':['client','clientele','fiche contact'],
    'Projets':['projet','planning projet','cahier des charges'],
    'Réunions':['reunion','compte rendu','ordre du jour','meeting'],
    'Ressources humaines':['paie','salaire','conges','ressources humaines','recrutement'],
    'Administratif':['attestation','certificat','identite','administratif','courrier'],
    'Impôts':['impots','impot','fiscal','fiscale','declaration revenus','avis imposition'],
    'Banque':['banque','bancaire','releve de compte','rib','iban'],
    'Santé':['sante','ordonnance','medical','medecin','analyse medicale','vaccination'],
    'Logement':['logement','loyer','bail','quittance','electricite','habitation'],
    'Véhicule':['vehicule','voiture','carte grise','controle technique','automobile'],
    'Assurances':['assurance','sinistre','assureur'],
}
TEXT={'.txt','.md','.csv','.log','.rtf'}
IMAGES={'.png','.jpg','.jpeg','.bmp','.tif','.tiff','.webp'}
MEDIA={'.mp3': 'Musique','.wav':'Musique','.flac':'Musique','.m4a':'Musique','.mp4':'Vidéos','.mov':'Vidéos','.avi':'Vidéos','.mkv':'Vidéos'}

def folded(value):return re.sub(r'[^a-z0-9]+',' ',unicodedata.normalize('NFKD',value.casefold()).encode('ascii','ignore').decode()).strip()

def folder_specs(profile,categories=None):
    if profile not in PROFILES:raise ValueError('Profil inconnu.')
    if categories is not None and (not isinstance(categories,list) or any(not isinstance(v,str) for v in categories)):raise ValueError('Liste de dossiers invalide.')
    wanted=set(categories if categories is not None else PROFILES[profile]);wanted.add(INBOX)
    if not wanted<=set(PROFILES[profile]):raise ValueError('Dossiers inconnus.')
    result=[]
    for index,name in enumerate(PROFILES[profile]):
        if name not in wanted:continue
        color=COLORS[index%len(COLORS)];result.append(dict(path=name,color=color))
        if profile in SCHOOL and name not in (INBOX,'Documents école','Orientation','Projets'):
            result.extend(dict(path=name+'/'+child,color=color) for child in ('Cours','Exercices','Évaluations'))
    return result

def _link(path):return path.is_symlink() or path.is_junction()

def inside(root,path,regular=False):
    root=Path(root).absolute();path=Path(path).absolute()
    if '..' in path.parts or (path!=root and root not in path.parents):raise ValueError('Emplacement hors de cet espace.')
    current=path
    while True:
        if _link(current):raise ValueError('Les liens et jonctions sont ignorés.')
        if current==root:break
        current=current.parent
    resolved=path.resolve()
    if root.resolve()!=root or (resolved!=root and root not in resolved.parents):raise ValueError('Emplacement redirigé.')
    if regular and not stat.S_ISREG(path.lstat().st_mode):raise ValueError('Fichier ordinaire attendu.')
    return path

def load_space(root):
    root=Path(root).resolve();inside(root,root)
    manifest=inside(root,root/'.organisator/space.json',True)
    if manifest.stat().st_size>64000:raise ValueError('Configuration invalide.')
    config=json.loads(manifest.read_text(encoding='utf-8'))
    if config.get('version')!=1 or config.get('profile') not in PROFILES:raise ValueError('Cet espace n’est pas un dossier Organisator.')
    config['folders']=folder_specs(config['profile'],config.get('categories'))
    return root,config

def create_space(desktop,name,profile,categories=None,icons=None):
    name=name.strip();desktop=Path(desktop).resolve()
    if not name or len(name)>80 or name in ('.','..') or name.rstrip(' .')!=name or re.search(r'[<>:"/\\|?*\x00-\x1f]',name) or re.match(r'^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)',name,re.I):raise ValueError('Choisissez un nom de dossier valide.')
    specs=folder_specs(profile,categories)
    if not desktop.is_dir():raise ValueError('Le Bureau est introuvable.')
    root=desktop/name;root.mkdir(exist_ok=False)
    meta=root/'.organisator';meta.mkdir()
    config=dict(version=1,id=uuid.uuid4().hex,profile=profile,categories=[item['path'] for item in specs if '/' not in item['path']])
    (meta/'space.json').write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8')
    for spec in specs:(root/spec['path']).mkdir(parents=True,exist_ok=True)
    if icons:
        from shared.organizer_icons import install_icons
        config['icon_warnings']=install_icons(root,specs,Path(icons))
    return root,config

def incoming(root,limit=2000):
    root,config=load_space(root);result=[];warnings=[]
    def visit(directory,depth=0):
        if depth>8 or len(result)>=limit:return
        for path in sorted(directory.iterdir(),key=lambda p:p.name.casefold()):
            if path.name.startswith(('.','~$')) or path.name.casefold()=='desktop.ini' or path.suffix.lower() in ('.tmp','.part','.crdownload'):continue
            try:
                inside(root,path)
                if path.is_file():result.append(path)
                elif path.is_dir() and depth<8:visit(path,depth+1)
            except (ValueError,OSError) as error:warnings.append(path.name+' : '+str(error))
            if len(result)>=limit:break
    for path in root.iterdir():
        if path.is_file() and not path.name.startswith('.') and path.name.casefold()!='desktop.ini':
            try:inside(root,path,True);result.append(path)
            except (ValueError,OSError) as error:warnings.append(path.name+' : '+str(error))
    inbox=inside(root,root/INBOX)
    if inbox.is_dir():visit(inbox)
    if len(result)>=limit:warnings.append('Analyse limitée à '+str(limit)+' fichiers ; relancez après le classement.')
    return result[:limit],warnings

def read_text(path,ocr=None):
    path=Path(path);ext=path.suffix.lower();size=path.stat().st_size
    if ext in TEXT:
        with path.open('rb') as stream:raw=stream.read(256000)
        try:return raw.decode('utf-8-sig'),'Texte'
        except UnicodeDecodeError:return raw.decode('cp1252',errors='replace'),'Texte'
    if ext=='.pdf':
        import pymupdf
        with DOCUMENT_LOCK,pymupdf.open(path) as doc:
            if doc.needs_pass:return '','PDF protégé'
            return '\n'.join(doc[i].get_text()[:50000] for i in range(min(3,len(doc))))[:120000],'PDF'
    if ext in ('.docx','.odt','.pptx','.xlsx') and size<40*1024**2:
        with zipfile.ZipFile(path) as archive:
            members=[m for m in archive.infolist() if m.filename in ('word/document.xml','content.xml','xl/sharedStrings.xml') or re.fullmatch(r'ppt/slides/slide[1-3]\.xml',m.filename)]
            if sum(m.file_size for m in members)>4*1024**2:return '','Document volumineux'
            texts=[]
            for member in members:
                node=ET.fromstring(archive.read(member));texts.extend(node.itertext())
            return ' '.join(texts)[:120000],'Document'
    if ext in IMAGES and ocr and size<20*1024**2:return ocr(path)[:120000],'Image · texte reconnu'
    return '',('Image' if ext in IMAGES else 'Aperçu textuel indisponible')

def classify(path,text,config):
    name=' '+folded(Path(path).stem)+' ';body=' '+folded(text[:60000])+' ';scores=[]
    for category in config['categories']:
        if category==INBOX:continue
        score=0;hits=[]
        for keyword in KEYWORDS.get(category,[]):
            if category=='Langues' and 'Anglais' in config['categories'] and keyword in ('anglais','english'):continue
            term=' '+keyword+' '
            if term in name:score+=6;hits.append(keyword)
            if term in body:score+=min(4,body.count(term));hits.append(keyword)
        if score:scores.append((score,category,hits))
    scores.sort(reverse=True)
    if scores:
        best,category,hits=scores[0];runner=scores[1][0] if len(scores)>1 else 0
        if best==runner:return INBOX,0.,'Plusieurs thèmes possibles'
        confidence=.96 if best>=6 and best-runner>=3 else .78 if best>=3 and best>runner else .6
        target=category
        if config['profile'] in SCHOOL and any(f['path']==category+'/Cours' for f in config['folders']):
            context=name+body[:4000];kind='Évaluations' if any(' '+k+' ' in context for k in ('controle','evaluation','examen','brevet')) else 'Exercices' if any(' '+k+' ' in context for k in ('exercice','exercices','devoir','devoirs')) else 'Cours'
            target+='/'+kind
        return target,confidence,'Indices : '+', '.join(dict.fromkeys(hits))
    ext=Path(path).suffix.lower();target=MEDIA.get(ext)
    if target in config['categories']:return target,.92,'Type de fichier multimédia'
    if ext in IMAGES:
        target='Photos' if 'Photos' in config['categories'] else 'Images' if 'Images' in config['categories'] else None
        if target:return target,.7,'Image sans thème reconnu · à vérifier'
    if ext in ('.zip','.7z','.rar') and 'Archives' in config['categories']:return 'Archives',.85,'Archive conservée sans extraction'
    return INBOX,0.,'Destination à choisir'

@dataclass
class Proposal:
    source:str
    destination:str
    confidence:float
    reason:str
    size:int
    modified:int
    text:str=''
    kind:str=''

def analyze(root,cancel=None,ocr=None):
    root,config=load_space(root);paths,warnings=incoming(root);proposals=[];ocr_count=0
    for path in paths:
        if cancel and cancel.is_set():break
        try:
            before=path.stat();text='';kind='';error=''
            try:
                use_ocr=ocr if path.suffix.lower() in IMAGES and ocr_count<12 else None
                if use_ocr:ocr_count+=1
                text,kind=read_text(path,use_ocr)
            except Exception as exc:error=' · aperçu indisponible';kind='Aperçu indisponible'
            after=path.stat()
            if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):continue
            target,confidence,reason=classify(path,text,config)
            proposals.append(Proposal(str(path.relative_to(root)),target,confidence,reason+error,before.st_size,before.st_mtime_ns,text,kind))
        except (OSError,ValueError) as error:warnings.append(path.name+' : '+str(error))
    return proposals,warnings

def _journal(root,item):
    journal=inside(root,root/'.organisator/moves.jsonl')
    with journal.open('a',encoding='utf-8') as stream:stream.write(json.dumps(item,ensure_ascii=False)+'\n');stream.flush();os.fsync(stream.fileno())

def _digest(path,cancel=None):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):
            if cancel and cancel.is_set():raise ValueError('Opération interrompue.')
            digest.update(block)
    return digest.hexdigest()

def _rename(source,destination):
    if os.name!='nt':raise OSError('Les déplacements sans écrasement de cette version nécessitent Windows.')
    # Windows os.rename is atomic on this volume and refuses an existing target.
    os.rename(source,destination)

def apply_moves(root,proposals,cancel=None):
    root,config=load_space(root);allowed={item['path'] for item in config['folders']};batch=uuid.uuid4().hex;moved=[];errors=[]
    for proposal in proposals:
        if cancel and cancel.is_set():break
        try:
            if proposal.destination not in allowed or proposal.destination==INBOX:raise ValueError('Choisissez un dossier de classement.')
            source=inside(root,root/proposal.source,True);current=source.stat()
            if (current.st_size,current.st_mtime_ns)!=(proposal.size,proposal.modified):raise ValueError('Fichier modifié depuis l’analyse : analysez de nouveau.')
            directory=inside(root,root/proposal.destination)
            if not directory.is_dir():raise ValueError('Dossier de destination absent.')
            digest=_digest(source,cancel)
            if (source.stat().st_size,source.stat().st_mtime_ns)!=(proposal.size,proposal.modified):raise ValueError('Fichier en cours de modification.')
            for index in range(10000):
                destination=directory/(source.name if index==0 else source.stem+' ('+str(index)+')'+source.suffix)
                if destination==source:raise ValueError('Déjà dans ce dossier.')
                if destination.exists():continue
                operation=dict(id=uuid.uuid4().hex,batch=batch,source=proposal.source,destination=str(destination.relative_to(root)),sha256=digest,file_id=[current.st_dev,current.st_ino],time=time.time())
                _journal(root,dict(operation,state='planned'))
                try:_rename(source,destination)
                except FileExistsError:_journal(root,dict(operation,state='skipped'));continue
                moved.append(operation)
                try:_journal(root,dict(operation,state='moved'))
                except OSError:errors.append(source.name+' : déplacé, journal initial conservé pour annulation.')
                break
            else:raise ValueError('Trop de noms identiques.')
        except (OSError,ValueError) as error:errors.append(proposal.source+' : '+str(error))
    return moved,errors

def undo_last(root,cancel=None):
    root,config=load_space(root);journal=inside(root,root/'.organisator/moves.jsonl')
    if not journal.exists():return [],[]
    if journal.stat().st_size>20*1024**2:raise ValueError('Historique volumineux : annulation manuelle nécessaire.')
    operations={};undone=set()
    for line in journal.read_text(encoding='utf-8').splitlines():
        try:item=json.loads(line)
        except ValueError:continue
        if not isinstance(item,dict):continue
        if item.get('state') in ('undone','skipped'):undone.add(item.get('id'))
        elif item.get('state') in ('planned','moved'):operations[item['id']]=item
    candidates=[op for op in operations.values() if op['id'] not in undone and (root/op['destination']).is_file()]
    if not candidates:return [],[]
    batch=candidates[-1]['batch'];restored=[];errors=[]
    for item in reversed(candidates):
        if item['batch']!=batch:continue
        if cancel and cancel.is_set():break
        try:
            source=inside(root,root/item['destination'],True);target=inside(root,root/item['source'])
            if target.exists():raise ValueError('L’emplacement d’origine est occupé.')
            file_stat=source.stat()
            if item.get('file_id')!=[file_stat.st_dev,file_stat.st_ino] or _digest(source,cancel)!=item['sha256']:raise ValueError('Le fichier a changé ; il reste à sa place.')
            if not target.parent.is_dir():raise ValueError('Le dossier d’origine n’existe plus.')
            _rename(source,target);_journal(root,dict(item,state='undone'));restored.append(item)
        except (OSError,ValueError,KeyError) as error:errors.append(item.get('destination','')+' : '+str(error))
    return restored,errors
