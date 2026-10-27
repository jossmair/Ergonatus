from pathlib import Path
import subprocess
import json
import os
import re
from html import escape
from shared.catalog import suite_root

def format_text(text,mode='paragraphs'):
    """Reflow recognised text only; never invent content or document styling."""
    text=text.replace('\r\n','\n').replace('\r','\n')
    if mode in ('lines','columns'):return text
    if mode!='paragraphs':raise ValueError('Mise en page inconnue.')
    paragraphs=[];current=[]
    for line in text.split('\n'):
        line=re.sub(r'[\t ]+',' ',line).strip()
        if not line:
            if current:paragraphs.append(' '.join(current));current=[]
        elif re.match(r'^(?:[•●–-]|\d+[.)])\s',line):
            if current:paragraphs.append(' '.join(current))
            current=[line]
        else:current.append(line)
    if current:paragraphs.append(' '.join(current))
    return '\n\n'.join(paragraphs)

def clipboard_html(text,mode='paragraphs'):
    """Clean rich text plus a plain-text fallback; no image or application colours."""
    if mode=='columns' and '\t' in text:
        body='<table><tbody>'+''.join('<tr>'+''.join('<td>'+escape(cell)+'</td>' for cell in line.split('\t'))+'</tr>' for line in text.splitlines())+'</tbody></table>'
    elif mode=='paragraphs':body=''.join('<p>'+escape(part).replace('\n','<br>')+'</p>' for part in text.split('\n\n'))
    else:body='<div>'+escape(text).replace('\n','<br>')+'</div>'
    return '<html><body><!--StartFragment-->'+body+'<!--EndFragment--></body></html>'

def recognize_data(path):
    path=Path(path).resolve()
    if not path.is_file():raise ValueError('Image absente.')
    powershell=Path(os.environ.get('SystemRoot','C:/Windows'))/'System32/WindowsPowerShell/v1.0/powershell.exe'
    result=subprocess.run([str(powershell),'-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(suite_root()/'scripts/windows_ocr.ps1'),'-ImagePath',str(path)],capture_output=True,timeout=60,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if result.returncode:raise ValueError('OCR Windows indisponible : '+result.stderr.decode('utf-8',errors='replace')[-500:])
    return json.loads(result.stdout.decode('utf-8-sig'))

def recognize(path):
    data=recognize_data(path)
    # Preserve lines; larger word gaps become tabs for simple column layouts.
    lines=[]
    for line in data.get('lines',[]):
        words=line['words'];parts=[];previous=None
        for word in words:
            if previous is not None:parts.append('\t' if word['x']-previous['x']-previous['width']>max(24,word['height']*2) else ' ')
            parts.append(word['text']);previous=word
        lines.append(''.join(parts))
    return '\n'.join(lines) or data.get('text','')
