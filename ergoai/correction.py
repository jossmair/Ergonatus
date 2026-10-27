"""Local French grammar rules; no generative rewriting of the user's text."""
import sys,threading,re
from shared.catalog import suite_root

_lock=threading.Lock()
_checker=None

def edit_distance(left,right):
    previous=list(range(len(right)+1))
    for i,a in enumerate(left,1):
        current=[i]
        for j,b in enumerate(right,1):current.append(min(current[-1]+1,previous[j]+1,previous[j-1]+(a!=b)))
        previous=current
    return previous[-1]


def spelling_choice(word,suggestions):
    if not word or len(word)>50 or not suggestions:return None
    ranked=[(edit_distance(word.casefold(),candidate.casefold()),candidate) for candidate in set(suggestions)]
    ranked.sort()
    best=ranked[0][0]
    if best>min(2,max(1,len(word)//5)):return None
    nearest=[candidate for distance,candidate in ranked if distance==best]
    return nearest[0] if len(nearest)==1 else None


def punctuate(text,following=''):
    """Requested rule: sentence closure only for paragraphs over five words."""
    parts=[]
    paragraphs=text.splitlines(keepends=True)
    for index,paragraph in enumerate(paragraphs):
        match=re.match(r'^(\s*)(.*?)(\s*)$',paragraph,re.DOTALL)
        leading,body,trailing=match.groups()
        if len(re.findall(r"\b\w+(?:[’'-]\w+)*\b",body))>5:
            # Keep existing stops, questions, ellipses and punctuation before quotes.
            core=body.rstrip('»”"\')]} \u00a0\u202f')
            closing=body[len(core):]
            existing_after=index==len(paragraphs)-1 and following.lstrip().startswith(tuple('.!?…:;,'))
            if core and core[-1] not in '.!?…:;' and not existing_after:body=core+'.'+closing
            if body and body[0].islower():body=body[0].upper()+body[1:]
        parts.append(leading+body+trailing)
    return ''.join(parts)


def future_conditions(text,checker):
    from grammalecte.fr import conj
    output=[]
    for sentence in re.split(r'(?<=[.!?])(?=\s)',text):
        tokens=list(re.finditer(r"[^\W\d_]+",sentence))
        words=[token.group().casefold() for token in tokens]
        temporal=re.search(r"\b(?:demain|après-demain|prochain(?:e|s|es)?)\b",sentence,re.I)
        conditions=[i for i,word in enumerate(words) if word=='si']
        if not temporal or not conditions:output.append(sentence);continue
        present=False
        for i in conditions:
            for word in words[i+1:i+12]:
                morph=checker.getMorph(word)
                finite=[m for m in morph if ':V' in m and any(tag in m for tag in (':Ip:',':Iq:',':If:',':K:',':Is:'))]
                if finite:
                    present=any(':Ip:' in m for m in finite);break
            if present:break
        if not present:output.append(sentence);continue
        edits=[];persons={'je':':1s','j':':1s','tu':':2s','il':':3s','elle':':3s','on':':3s','nous':':1p','vous':':2p','ils':':3p','elles':':3p'}
        for i,word in enumerate(words):
            person=persons.get(words[i-1]) if i else None
            if not person:continue
            candidates=set()
            for morph in checker.getMorph(word):
                if ':K:' not in morph:continue
                lemma=morph[1:].split('/')[0]
                if lemma in ('vouloir','pouvoir','aimer','souhaiter'):continue
                form=conj.getConj(lemma,':If',person)
                if form:candidates.add(form)
            if len(candidates)==1:edits.append((tokens[i].start(),tokens[i].end(),candidates.pop()))
        for start,end,replacement in reversed(edits):sentence=sentence[:start]+replacement+sentence[end:]
        output.append(sentence)
    return ''.join(output)


def correct_rules(text,cancel=None,following=''):
    if not isinstance(text,str) or not text.strip() or len(text)>12000:
        raise ValueError('Sélectionnez un passage de 1 à 12 000 caractères.')
    global _checker
    with _lock:
        if _checker is None:
            sys.path.insert(0,str(suite_root()/'ergoai/grammar/vendor'))
            from grammalecte import GrammarChecker
            _checker=GrammarChecker('fr')
        current=future_conditions(text,_checker.getSpellChecker());count=int(current!=text)
        for _ in range(6):
            if cancel and cancel.is_set():raise ValueError('Correction annulée.')
            offset=0;edits=[]
            for paragraph in current.splitlines(keepends=True):
                grammar,spelling=_checker.getParagraphErrors(paragraph,bSpellSugg=True)
                for error in list(grammar):
                    suggestions=error.get('aSuggestions',[])
                    if len(suggestions)==1:edits.append((offset+error['nStart'],offset+error['nEnd'],suggestions[0]))
                for error in spelling:
                    word=error.get('sValue','')
                    # Protect capitalised names away from sentence starts.
                    before=paragraph[:error['nStart']].rstrip()
                    if word[:1].isupper() and before and before[-1] not in '.!?…':continue
                    candidate=spelling_choice(word,error.get('aSuggestions',[]))
                    if candidate:edits.append((offset+error['nStart'],offset+error['nEnd'],candidate))
                offset+=len(paragraph)
            end=len(current)+1;updated=current
            for start,stop,replacement in sorted(set(edits),reverse=True):
                if 0<=start<stop<=len(current) and stop<=end:
                    updated=updated[:start]+replacement+updated[stop:];end=start;count+=1
            if updated==current:break
            current=updated
        polished=punctuate(current,following)
        if polished!=current:count+=1
        remaining=[];offset=0
        for paragraph in polished.splitlines(keepends=True):
            grammar,spelling=_checker.getParagraphErrors(paragraph,bSpellSugg=True)
            for error in list(grammar)+spelling:
                start=error['nStart'];end=error['nEnd']
                remaining.append(dict(start=offset+start,end=offset+end,text=paragraph[start:end],suggestions=error.get('aSuggestions',[])[:6],message=error.get('sMessage','Mot à vérifier.'),rule=error.get('sRuleId','spelling'),kind='grammar' if 'sRuleId' in error else 'spelling'))
            offset+=len(paragraph)
        return dict(text=polished,changes=count,remaining=remaining,engine='Grammalecte 2.3.0')


def align_selection_boundary(source,generated,following):
    if following.lstrip().startswith(tuple('.!?…:;,')) and not source.rstrip().endswith(tuple('.!?…')):
        core=generated.rstrip();trailing=generated[len(core):]
        return core.rstrip('.!?…')+trailing
    return generated


def correct(text,cancel=None,following=''):
    if not isinstance(text,str) or not text.strip() or len(text)>12000:raise ValueError('Sélectionnez un passage de 1 à 12 000 caractères.')
    from ergoai.proofreading_client import correct as neural_correct
    prepared=correct_rules(text,cancel,following)
    try:neural=neural_correct(prepared['text'],cancel)
    except (ValueError,OSError,EOFError,RuntimeError) as error:
        if cancel and cancel.is_set():raise ValueError('Correction annulée.') from error
        message=str(error)
        # A declined linguistic rewrite is not a resource failure: do not hide
        # an integrity check or a cancellation behind an automatic fallback.
        unavailable=any(marker in message.casefold() for marker in ('ram disponible','mémoire','memory','ne répond pas','n’a pas démarré','absent','indisponible','connexion','pipe','winerror')) or isinstance(error,(OSError,EOFError))
        if not unavailable:raise
        prepared.update(engine='Grammalecte 2.3.0 · mode économe',degraded=True,warning='IA indisponible : correction grammaticale locale appliquée. Les points incertains restent à vérifier.',model=None,seconds=0)
        return prepared
    generated=align_selection_boundary(text,neural['text'],following)
    result=correct_rules(generated,cancel,following)
    result['changes']+=prepared['changes']
    result['changes']+=int(neural['text']!=text)
    result['engine']='Luth 1.7B / moteur Redactor + vérification grammaticale'
    result['model']=neural['model'];result['seconds']=neural['seconds']
    return result
