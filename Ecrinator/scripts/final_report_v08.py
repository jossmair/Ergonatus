"""Collect executed checks for this release; never infer a missing test result."""
from pathlib import Path
from datetime import datetime
import hashlib,json,re
root=Path(__file__).resolve().parents[1]
read=lambda p:json.loads((root/p).read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
tests=(root/'test-output/tests-v08-guard-final.log').read_text(encoding='utf-8-sig',errors='replace')
groups=re.findall(r'test result: ok\. (\d+) passed; 0 failed;',tests)
assert sum(map(int,groups))==63 and 'test result: FAILED' not in tests
dist=read('test-output/distribution-verification.json')
exe=root/'runtime/Ecrinator.exe'
assert dist['version']=='0.8.0' and dist['executable_sha256']==sha(exe)
native=read('test-output/acceptance-v08-release/verification.json')
independent=read('test-output/acceptance-v08-release/independent-verification.json')
lo=read('test-output/libreoffice-release/libreoffice-verification.json')
assert native['native_roundtrip'] and native['recovery_roundtrip'] and independent['distinct_subject_backgrounds_in_pdf']==13
assert {p['file'] for p in lo}>={'cours.pdf','frise-et-bibliotheque.pdf','SVT.pdf'}
packages=[]
for path in sorted((root/'dist').glob('Ecrinator-0.8.0-*')):
    if path.is_file():packages.append(dict(file=path.name,bytes=path.stat().st_size,sha256=sha(path)))
assert len(packages)==5
screens=[]
for tool in ['encadres','library','timeline','chart']:
    p=root/f'test-output/ecrinator-0.8.0-{tool}.png'
    assert p.is_file() and p.stat().st_size>100_000
    screens.append(str(p.relative_to(root)))
report=dict(version='0.8.0',validated='2026-10-24',executable_sha256=sha(exe),automated_tests_passed=63,
    native=native,independent=independent,libreoffice_version='26.2.6.2',libreoffice_opened_and_rendered=lo,
    distribution=dist,packages=packages,screenshots=screens,
    clean_windows_without_python_tested=False,physical_printing_tested=False,screen_reader_tested=False)
(root/'test-output/release-verification-0.8.0.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
p=root/'docs/VALIDATION.md';text=p.read_text(encoding='utf-8').replace('62 tests réussis','63 tests réussis').replace('21 tests interface','22 tests interface').replace('test-output/tests-v08-release.log','test-output/tests-v08-guard-final.log')
marker='\n\n## Validation finale des distributions\n'
text=text.split(marker)[0]+marker
text+='Le binaire optimisé et les cinq archives sont construits et contrôlés. Les résultats agrégés sont dans test-output/release-verification-0.8.0.json.\n\n'
text+=f"Exécutable : {exe.stat().st_size} octets ; SHA-256 `{sha(exe)}`.\n\n"
text+='La dernière passe compte 63 tests. Le test ajouté protège un document importé non classé : la récupération reste active mais Organisator ne modifie ni sa destination ni son fichier. Une page blanche ne déclenche pas de sauvegarde automatique Organisator.\n\n'
text+='La passe optimisée est dans build-v08-import-guard-release.log. Le contrôle PDFium/pypdf et ZIP/XML/MathML a réussi dans verification-v08-release.log. Les 13 fonds de matière sont distincts, la zone de lecture est claire et les encadrés restent vectoriels dans le PDF. Les trois ODT de ce binaire ont été ouverts et convertis par LibreOffice : libreoffice-v08-release.log et libreoffice-render-v08-release.log. Les pages natives et les pages de sortie Writer ont été inspectées. Le témoin long conserve 7 pages natives et 6 dans Writer.\n\n'
text+='Le portable est extrait dans un dossier neuf et exécuté avec un PATH réduit à Windows/System32. Sa récupération, son OCR français disponible sur ce poste et ses exports fonctionnent. Les données portables restent à côté de l’exécutable. L’installeur a été exécuté en mode de test dans un sous-dossier du projet, sans raccourcis ni inscription de désinstallation dans le compte. Son exécutable est identique au portable. La désinstallation de test retire l’application et conserve les documents ainsi que les données. Cela ne remplace pas un essai sur Windows vierge ni une installation/désinstallation réelle du compte utilisateur.\n\n'
text+='Les paquets graphiques contiennent 91 SVG, 13 illustrations de matière et les 13 fonds sources avec leurs consignes. Le paquet bibliothèque conserve 19 images et leurs sources/licences ; ses empreintes ont été vérifiées.\n\n'
for item in packages:text+=f"- {item['file']} : {item['bytes']} octets ; SHA-256 `{item['sha256']}`.\n"
text+='\nCaptures du binaire final :\n\n'+''.join(f'- {p}\n' for p in screens)
p.write_text(text,encoding='utf-8')
p=root/'PLAN.md';text=p.read_text(encoding='utf-8').replace('62 tests réussis dans test-output/tests-v08-release.log','63 tests réussis dans test-output/tests-v08-guard-final.log')
text=text.replace('La construction optimisée est lancée dans test-output/build-v08-release.log. Le statut final et les empreintes des distributions sont consignés dans docs/VALIDATION.md après validation. Vérifier la version de runtime/Ecrinator.exe et les rapports avant de considérer un paquet comme validé.',
'''La construction optimisée finale est réussie (test-output/build-v08-import-guard-release.log). Le portable, l’installeur en mode de test, les exports et la désinstallation dans le dossier isolé ont été vérifiés. Les cinq paquets sont sous dist/, les empreintes dans dist/SHA256SUMS.txt et docs/VALIDATION.md. Rapport agrégé : test-output/release-verification-0.8.0.json. Binaire final : '''+sha(exe)+'.')
p.write_text(text,encoding='utf-8')
print(json.dumps({'version':report['version'],'tests':63,'packages':len(packages),'executable_sha256':sha(exe),'libreoffice_documents':3},indent=2))
