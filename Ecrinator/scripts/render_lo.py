"""Independent LibreOffice/PDFium inspection of our synthetic ODT fixtures."""
from pathlib import Path
import json,sys
from pypdf import PdfReader
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root.parent/'PDFinator/.tools/oracle'))
import pypdfium2 as pdfium
folder=Path(sys.argv[1]).resolve()
out=[]
for file in sorted(folder.glob('*.pdf')):
    reader=PdfReader(file,strict=True)
    text='\n'.join(p.extract_text() for p in reader.pages)
    if file.stem=='cours':
        for phrase in ['Les fractions','numérateur','Exercice 85']:assert phrase in text,phrase
    if file.stem=='frise-et-bibliotheque':
        assert 'La Révolution française' in text
        assert 'commons.wikimedia.org' not in text, 'Image credits must stay off the pages'
    with pdfium.PdfDocument(file) as pdf:
        image=pdf[0].render(scale=1.5).to_pil()
        image.save(folder/(file.stem+'-page1.png'))
    out.append({'file':file.name,'pages':len(reader.pages),'text_characters':len(text),'selectable_french_text':True})
assert len(out)>=3
(folder/'libreoffice-verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(out,ensure_ascii=False,indent=2))
