"""Conservative hidden reading order and paragraphs from OCR word geometry."""
from statistics import median
import re

def paragraphs(rows):
    if not rows:return ''
    rows=sorted(rows,key=lambda row:(row['y'],row['x']))
    height=median(row['height'] for row in rows);width=max(row['right'] for row in rows)-min(row['x'] for row in rows)
    result=[];current='';previous=None
    for row in rows:
        text=row['text'].strip()
        if not text:continue
        gap=previous is not None and row['y']-previous['bottom']>height*.8
        indent=previous is not None and row['x']-previous['x']>height*1.2 and re.search(r'[.!?:…]$',current)
        short=previous is not None and previous['right']-previous['x']<width*.72 and re.search(r'[.!?…]$',current)
        if current and (gap or indent or short):result.append(current);current=''
        if current.endswith('-') and text[0].islower():current=current[:-1]+text
        else:current=(current+' '+text).strip()
        previous=row
    if current:result.append(current)
    return '\n\n'.join(result)

def reconstruct(data):
    words=[word for line in data.get('lines',[]) for word in line.get('words',[]) if word.get('text','').strip()]
    if not words:return data.get('text','').strip()
    height=median(max(1,word.get('height',1)) for word in words)
    span=max(word['x']+word['width'] for word in words)-min(word['x'] for word in words)
    rows=[]
    for line in data.get('lines',[]):
        groups=[];current=[];last=None
        for word in sorted(line.get('words',[]),key=lambda word:word['x']):
            if last and word['x']-last['x']-last['width']>max(height*4,span*.16):groups.append(current);current=[]
            current.append(word);last=word
        if current:groups.append(current)
        for group in groups:
            rows.append(dict(text=' '.join(word['text'] for word in group),x=min(word['x'] for word in group),y=min(word.get('y',0) for word in group),right=max(word['x']+word['width'] for word in group),bottom=max(word.get('y',0)+word['height'] for word in group),height=median(word['height'] for word in group)))
    columns=[]
    for row in sorted(rows,key=lambda row:row['x']):
        if not columns or row['x']-columns[-1][0]['x']>max(70,span*.25):columns.append([])
        columns[-1].append(row)
    if len(columns)>1 and all(len(column)>=2 for column in columns):return '\n\n'.join(paragraphs(column) for column in columns)
    return paragraphs(rows)

def recognize_reading(path,double_page=False):
    from shared.ocr import recognize_data
    if not double_page:return reconstruct(recognize_data(path))
    from PySide6.QtGui import QImage
    from pathlib import Path
    path=Path(path);image=QImage(str(path))
    if image.isNull():raise ValueError('Photo illisible.')
    middle=image.width()//2;texts=[]
    for index,(x,width) in enumerate(((0,middle),(middle,image.width()-middle))):
        part=path.with_name(path.stem+f'-page-{index}.png')
        try:
            if not image.copy(x,0,width,image.height()).save(str(part)):raise ValueError('Page illisible.')
            texts.append(reconstruct(recognize_data(part)))
        finally:part.unlink(missing_ok=True)
    return '\n\n'.join(text for text in texts if text.strip())
