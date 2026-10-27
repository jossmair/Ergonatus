"""Local translation requests with explicit source and destination languages."""
import re

LANGUAGES={
    'fr':('Français','French',0x0c),'en':('Anglais','English',0x09),
    'es':('Espagnol','Spanish',0x0a),'de':('Allemand','German',0x07),
    'it':('Italien','Italian',0x10),'pt':('Portugais','Portuguese',0x16),
    'ar':('Arabe','Arabic',0x01),'uk':('Ukrainien','Ukrainian',0x22),
}


def translate(text,source,target,identifier,stop,current):
    from ergoai.translation_client import translate as infer
    if source not in LANGUAGES or target not in LANGUAGES:raise ValueError('Choisissez les deux langues.')
    if not text.strip():raise ValueError('Écrivez un message à traduire.')
    if len(text)>100000:raise ValueError('Le document est trop long. Traduisez-le en plusieurs parties.')
    if source==target:return text
    parts=[];chunk=''
    for sentence in re.split(r'(?<=[.!?؟])\s+|\n+',text):
        if len(chunk)+len(sentence)+1>1000 and chunk:parts.append(chunk);chunk=''
        while len(sentence)>1000:
            split=sentence.rfind(' ',0,1000)
            if split<1:split=1000
            if chunk:parts.append(chunk);chunk=''
            parts.append(sentence[:split]);sentence=sentence[split:].lstrip()
        chunk+=((' ' if chunk else '')+sentence)
    if chunk:parts.append(chunk)
    results=[]
    for index,part in enumerate(parts):
        if stop.is_set():raise ValueError('Traduction annulée.')
        current['id']=identifier+'-'+str(index)
        result=infer(part,source,target,cancel=stop)
        if stop.is_set():raise ValueError('Traduction annulée.')
        results.append(result['text'])
    return '\n\n'.join(results)


def matches_voice(attribute,language):
    if language not in LANGUAGES:return False
    for value in str(attribute).split(';'):
        try:
            if int(value.strip(),16)&0x3ff==LANGUAGES[language][2]:return True
        except ValueError:pass
    return False


def speak_language(speaker,text,language):
    """All displayed languages have a bundled voice; no Windows dependency."""
    from shared.translation_speech import speak
    return speak(speaker,text,language)
