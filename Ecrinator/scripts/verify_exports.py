"""Independent development checks; pypdf/PDFium are never shipped in the app."""
from pathlib import Path
import json
import hashlib
import sys
from zipfile import ZipFile, ZIP_STORED
from xml.etree import ElementTree as ET

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root.parent / 'PDFinator/.tools/oracle'))
import pypdfium2 as pdfium
from pypdf import PdfReader

folder = Path(sys.argv[1] if len(sys.argv) > 1 else root / 'test-output/acceptance-release').resolve()
report = json.loads((folder / 'verification.json').read_text(encoding='utf-8'))
history=PdfReader(folder/'frise-et-bibliotheque.pdf',strict=True)
assert 'commons.wikimedia.org' not in '\n'.join(p.extract_text()for p in history.pages)
assert 'commons.wikimedia.org' in (history.metadata.subject or ''), 'PDF metadata must retain attribution'
with ZipFile(folder/'frise-et-bibliotheque.odt')as attribution:
    assert 'commons.wikimedia.org' in attribution.read('meta.xml').decode('utf-8')
    assert 'meta:user-defined' in attribution.read('meta.xml').decode('utf-8')
    assert 'commons.wikimedia.org' not in attribution.read('content.xml').decode('utf-8')
reader = PdfReader(folder / 'cours.pdf', strict=True)
assert len(reader.pages) == report['pages']
assert all(abs(float(p.mediabox.width) - 595.276) < 0.1 and abs(float(p.mediabox.height) - 841.89) < 0.1 for p in reader.pages)
text = '\n'.join(p.extract_text() for p in reader.pages)
for expected in ['Mathématiques', 'Les fractions', 'Définition', 'numérateur', 'dénominateur', 'Élève' if 'Élève' in text else 'élève', 'Exercice 85']:
    assert expected in text, f'Text missing from PDF: {expected}'

with pdfium.PdfDocument(folder / 'cours.pdf') as pdf:
    assert len(pdf) == report['pages']
    for i in range(len(pdf)):
        page = pdf[i]
        bitmap = page.render(scale=1.2)
        assert bitmap.width > 700 and bitmap.height > 1000
        if i < 3:
            bitmap.to_pil().save(folder / f'pdfium-page-{i + 1}.png')
        bitmap.close()
        page.close()

packages = {}
subject_colors = {}
for file in sorted(folder.glob('bandeau-*.pdf')):
    with pdfium.PdfDocument(file) as pdf:
        page = pdf[0]
        bitmap = page.render(scale=1)
        rendered = bitmap.to_pil().convert('RGB')
        subject_colors[file.stem] = hashlib.sha256(rendered.crop((0,0,210,100)).tobytes()).hexdigest()
        assert min(rendered.getpixel((40,50))) < 245, 'Illustrated background missing from PDF'
        for x in (250, 360, 440):
            assert min(rendered.getpixel((x, 90))) >= 220, 'Information area is too dark behind the fields'
        banner_text = PdfReader(file, strict=True).pages[0].extract_text()
        assert 'Chapitre :' in banner_text and 'Un cours pour apprendre' in banner_text
        bitmap.close()
        page.close()
assert len(subject_colors) == 13 and len(set(subject_colors.values())) == 13, subject_colors
card_reader=PdfReader(folder / 'encadres.pdf',strict=True)
card_text='\n'.join(p.extract_text() for p in card_reader.pages)
for label in ['Définition','Propriété','Remarque','À retenir']:
    assert label in card_text, f'Editable card text missing: {label}'
card_curves=sum(op==b'c' for p in card_reader.pages for _,op in p.get_contents().operations)
# Full-width banner has no thick inset accent; four curves disappear.
assert card_curves >= 48, f'Rounded card paths missing from actual PDF: {card_curves} cubic segments'
for ext in ['odt', 'docx']:
    with ZipFile(folder / f'cours.{ext}') as archive:
        assert archive.testzip() is None
        xml_count = 0
        for entry in archive.namelist():
            if entry.endswith('.xml'):
                ET.fromstring(archive.read(entry))
                xml_count += 1
        if ext == 'odt':
            first = archive.infolist()[0]
            assert first.filename == 'mimetype' and first.compress_type == ZIP_STORED
            assert archive.read('mimetype') == b'application/vnd.oasis.opendocument.text'
            content = archive.read('content.xml').decode('utf-8')
            assert 'Les fractions' in content and 'draw:object' in content and 'draw:image' in content
            formula = archive.read('Formula1/content.xml').decode('utf-8')
            assert 'mfrac' in formula
            assert b'application/vnd.oasis.opendocument.formula' in archive.read('META-INF/manifest.xml')
        else:
            assert b'oMath' in archive.read('word/document.xml')
        packages[ext] = {'zip_crc': True, 'well_formed_xml_parts': xml_count}

result = {'pdf_pages': len(reader.pages), 'a4_points': [595.276, 841.89], 'pdf_selectable_french_text': True,
          'image_credits_in_metadata_not_pages':True,
          'independent_renderer': 'PDFium', 'rendered_pages': report['pages'], 'packages': packages,
          'rounded_card_cubic_segments':card_curves,'rounded_card_selectable_text':True,
          'distinct_subject_backgrounds_in_pdf':len(subject_colors),
          'full_width_subject_illustration':True,'optional_title_in_banner':True, 'light_reading_zone':True,
          'libreoffice_opening_tested': False}
(folder / 'independent-verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(result, ensure_ascii=False, indent=2))
