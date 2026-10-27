"""Read-only indexed Wiktionary definitions, with no LLM or network at lookup."""
import sqlite3,json,unicodedata,difflib,itertools
from urllib.parse import quote
from html import escape
from shared.catalog import suite_root

def normalize(text):return unicodedata.normalize('NFC',text.strip()).casefold().replace('’',"'")
def database():
    path=suite_root()/'Dictionnator/data/dictionary.sqlite3'
    if not path.is_file():raise ValueError('Le dictionnaire local est absent. Conservez le dossier Dictionnator/data avec le logiciel.')
    return sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)
def lookup(word,path=None):
    key=normalize(word)
    if not key or len(key)>100:raise ValueError('Entrez un mot ou une courte expression.')
    db=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) if path else database()
    try:
        rows=db.execute('SELECT word,pos,body FROM entries WHERE norm=? LIMIT 60',(key,)).fetchall()
        exact=[row for row in rows if row[0]==unicodedata.normalize('NFC',word.strip())]
        if exact:rows=exact
        if not rows:
            variants={'e':'eéèêë','a':'aàâä','i':'iîï','o':'oôö','u':'uùûü','c':'cç'}
            keys=[''.join(v) for v in itertools.islice(itertools.product(*(variants.get(c,c) for c in key)),512)]
            candidates=[r[0] for r in db.execute('SELECT DISTINCT word FROM entries WHERE norm IN ('+','.join('?'*len(keys))+')',keys)]
            # Indexed edit candidates reach words absent from the first
            # alphabetical prefix page (e.g. hipopotame -> hippopotame).
            if 3<=len(key)<=32:
                alphabet='abcdefghijklmnopqrstuvwxyzàâäçéèêëîïôöùûüœ'
                edits={key[:i]+key[i+1:] for i in range(len(key))}
                edits.update(key[:i]+key[i+1]+key[i]+key[i+2:] for i in range(len(key)-1))
                edits.update(key[:i]+letter+key[i:] for i in range(len(key)+1) for letter in alphabet)
                edits.update(key[:i]+letter+key[i+1:] for i in range(len(key)) for letter in alphabet)
                edits=list(edits)
                for offset in range(0,len(edits),200):
                    batch=edits[offset:offset+200]
                    candidates.extend(r[0] for r in db.execute('SELECT DISTINCT word FROM entries WHERE norm IN ('+','.join('?'*len(batch))+')',batch))
            for prefix in dict.fromkeys([key[:2],key[:1]]+[v+key[1:2] for v in {'e':['é','è','ê'],'a':['à','â'],'i':['î','ï'],'o':['ô'],'u':['ù','û'],'c':['ç']}.get(key[:1],[])]):
                candidates.extend(r[0] for r in db.execute('SELECT DISTINCT word FROM entries WHERE norm>=? AND norm<? LIMIT 1200',(prefix,prefix+'\uffff')))
            folded=lambda s:''.join(c for c in unicodedata.normalize('NFD',normalize(s)) if not unicodedata.combining(c))
            scored=sorted(set(candidates),key=lambda s:(-difflib.SequenceMatcher(None,folded(word),folded(s)).ratio(),not s.islower(),len(s),s))
            return dict(word=word,html='<h2>Mot introuvable</h2><p>Vérifiez son orthographe.</p>',suggestions=[s for s in scored[:6] if difflib.SequenceMatcher(None,folded(word),folded(s)).ratio()>=.65],found=False)
        html=[];seen=set();targets=[]
        for spelling,pos,raw in rows:
            html.append('<h2>'+escape(spelling)+'</h2><p style="color:#537089">'+escape(pos)+'</p>');html.append('<ol>')
            for sense in json.loads(raw):
                gloss=sense['gloss']
                if gloss in seen:continue
                seen.add(gloss);labels={'computing':'Informatique','figuratively':'Sens figuré','slang':'Argot','familiar':'Familier','archaic':'Vieilli','obsolete':'Désuet','vulgar':'Vulgaire','pejorative':'Péjoratif','mathematics':'Mathématiques','medicine':'Médecine','anatomy':'Anatomie','rare':'Rare','transitive':'Transitif','intransitive':'Intransitif','pronominal':'Pronominal','plural':'Pluriel','singular':'Singulier','feminine':'Féminin','masculine':'Masculin'};tags=' · '.join(labels.get(v,v) for v in sense.get('tags',[]) if v not in ('form-of',));html.append('<li><p>'+('<small>'+escape(tags)+'</small><br>' if tags else '')+escape(gloss)+'</p>')
                if sense.get('example') and len(sense['example'])<=220:html.append('<p style="color:#567285"><i>'+escape(sense['example'])+'</i></p>')
                html.append('</li>');targets.extend(sense.get('links',[]))
            html.append('</ol>')
        # An inflected word remains discoverable and brings its lemma definition.
        for target in list(dict.fromkeys(targets))[:3]:
            if normalize(target)==key:continue
            lemma=db.execute('SELECT word,pos,body FROM entries WHERE norm=? LIMIT 1',(normalize(target),)).fetchone()
            if lemma:
                html.append('<h3>Voir aussi : '+escape(lemma[0])+'</h3><ol>')
                for sense in json.loads(lemma[2]):html.append('<li>'+escape(sense['gloss'])+'</li>')
                html.append('</ol>')
        url='https://fr.wiktionary.org/wiki/'+quote(rows[0][0],safe='')+'#Français';html.append('<hr><small>Source : <a href="'+url+'">Wiktionnaire · contributeurs et historique</a>, extraction Kaikki. CC BY-SA / GFDL.</small>')
        return dict(word=rows[0][0],html=''.join(html),suggestions=[],found=True)
    finally:db.close()


def complete(prefix):
    key=normalize(prefix)
    if not 2<=len(key)<=60:return []
    db=database()
    try:
        candidates=[r[0] for r in db.execute('SELECT DISTINCT word FROM entries WHERE norm>=? AND norm<? LIMIT 100',(key,key+'\uffff'))]
        return sorted(candidates,key=lambda word:(len(word),not word.islower(),word))[:12]
    finally:db.close()
