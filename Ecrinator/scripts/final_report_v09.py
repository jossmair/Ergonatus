"""Collect only checks executed against the distributed 0.9.0 executable."""
from pathlib import Path
from datetime import datetime
import hashlib,json,re
root=Path(__file__).resolve().parents[1]
read=lambda p:json.loads((root/p).read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
log=(root/'test-output/tests-v09-final-guard.log').read_text(encoding='utf-8-sig',errors='replace')
groups=re.findall(r'test result: ok\. (\d+) passed; 0 failed;',log)
assert sum(map(int,groups))==69 and 'test result: FAILED'not in log
exe=root/'runtime/Ecrinator.exe';distribution=read('test-output/distribution-verification.json')
assert distribution['version']=='0.9.0'and distribution['executable_sha256']==sha(exe)
native=read('test-output/acceptance-v09-release/verification.json');independent=read('test-output/acceptance-v09-release/independent-verification.json')
lo=read('test-output/libreoffice-v09/libreoffice-verification.json');library=read('test-output/library-pack.json')
assert native['native_roundtrip']and native['library_images']==1203
assert independent['distinct_subject_backgrounds_in_pdf']==13
assert {p['file']for p in lo}>={'cours.pdf','frise-et-bibliotheque.pdf','SVT.pdf'}
assert sha(root/'runtime/library.eclib')==library['sha256']
packages=[dict(file=p.name,bytes=p.stat().st_size,sha256=sha(p))for p in sorted((root/'dist').glob('Ecrinator-0.9.0-*'))if p.is_file()]
assert len(packages)==5
screens=[]
for name in ['encadres','library']:
 p=root/f'test-output/ecrinator-0.9.0-{name}.png';assert p.is_file()and p.stat().st_size>100_000;screens.append(str(p.relative_to(root)))
report=dict(version='0.9.0',validated=datetime.now().isoformat(timespec='seconds'),executable_sha256=sha(exe),automated_tests_passed=69,native=native,independent=independent,library=library,libreoffice_version='26.2.6.2',libreoffice_opened_and_rendered=lo,distribution=distribution,packages=packages,screenshots=screens,clean_windows_without_python_tested=False,physical_printing_tested=False,screen_reader_tested=False)
(root/'test-output/release-verification-0.9.0.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
validation='''# Validation Écrinator 0.9.0

25 octobre 2026 — application Rust / Wordcraft 0.9.0. La mission initiale complète n’est pas déclarée achevée.

## Contrôles exécutés

69 tests réussis, sans échec : 9 bibliothèque Rust, 23 interface, 12 bandeaux, 3 encadrés, 1 icônes, 5 design pédagogique, 7 parcours scolaire, 9 outils visuels. Journal : test-output/tests-v09-final-guard.log. Données et brouillons isolés sous test-output ; aucun document de l’utilisateur utilisé.

Les tests couvrent le déplacement réel et vérifié entre Cours/Exercices/Évaluations, le refus de remplacer un fichier concurrent, la conservation d’une source modifiée ailleurs, les onglets, la récupération, les contrôles exclusifs du bandeau, la protection de son contenu et Ctrl+A limité au cours. La bibliothèque est vérifiée intégralement : décodage, dimensions et empreintes des images/miniatures. L’insertion et ses métadonnées sont annulables. Un véritable clic droit sur l’image affiche l’entrée Source et licence. Les anciennes lignes automatiques sont migrées sans supprimer une légende personnelle. Les propriétés publiques d’un ODT sans état privé conservent les sources.

## Exécutable et exports

L’exécutable distribué a produit des documents synthétiques A4, ODT, PDF et DOCX, rouverts par son contrôle intégré. Le pack library.eclib a été lu depuis le dossier de l’exécutable, avec vérification de ressources externes dans les trois catégories. Un lecteur PDF et PDFium indépendants contrôlent texte sélectionnable, dimensions, pagination et rendu. L’ODT est un véritable paquet ODF ; les XML et les sommes CRC sont contrôlés. L’attribution est absente du texte des pages et présente dans les propriétés ODT et PDF.

LibreOffice 26.2.6.2 a réellement ouvert et converti les documents ODT du binaire final, dans un profil de test privé. Les PDF produits ont été inspectés et rendus. Les angles des encadrés restent droits dans Writer ; frises/figures/graphiques utilisent des remplacements PNG. Les formules conservent MathML et une image de secours. La pagination de Writer peut différer de celle du moteur natif. Le bandeau et ses contrôles sont protégés dans Écrinator ; les structures publiques ODT restent éditables dans Writer.

## Distributions

Archives portable et installeur construits, contrôlés et exécutés dans des dossiers privés du workspace. Le pack de 1 203 images est identique dans runtime, portable et installation de test. Le mode portable écrit ses données à côté de son exécutable. L’installeur de test n’ajoute aucun raccourci ni entrée de désinstallation dans le compte ; sa désinstallation retire ses fichiers et conserve les cours et données de test. Ce contrôle ne remplace pas un essai sous un compte Windows vierge. Les dépendances PE inspectées et le PATH de l’essai n’impliquent pas Python.

La bibliothèque compte 191 cartes, 557 schémas SVT et 455 figures de physique, avec 51 thèmes. Les légendes originales OpenStax sont souvent anglaises. Les cartes Natural Earth sont des cartes de situation généralisées à 1:110m. Provenance historique, licences et adaptations sont distribuées. Les captures finales encadres/library et les rapports exacts sont listés dans test-output/release-verification-0.9.0.json.

## Limites restant à valider

Windows vierge sans Python ni LibreOffice, installation sous un autre compte, lecteurs d’écran/NVDA, DPI physiques 125/150/200 %, impression sur papier et performances sur poste scolaire modeste. L’OCR dépend du français installé dans Windows ; son recadrage visuel n’est pas terminé. L’import de documents externes peut perdre des détails non pris en charge. Le module musical spécialisé et une bibliothèque entièrement francisée restent des travaux distincts. Les frises ont des événements régulièrement espacés, sans échelle temporelle proportionnelle.

Les journaux intermédiaires restent conservés. Ils ont notamment permis de détecter un pack modifié pendant une compilation et une cible de test incorrecte pour une image en ligne. Ils ne sont pas utilisés comme validation finale.
'''.replace('\n+','\n')
(root/'docs/VALIDATION.md').write_text(validation,encoding='utf-8')
p=root/'PLAN.md';s=p.read_text(encoding='utf-8');a=s.index('Validation 0.9 en cours :');b=s.index('\n\n',a);s=s[:a]+'Validation 0.9 terminée le 25 octobre 2026 : 69 tests, contrôle indépendant PDF/ODT/DOCX, ouverture LibreOffice, captures natives et vérification des paquets portable/installeur. Rapport exact : test-output/release-verification-0.9.0.json. Runtime et distributions sont en 0.9.0. Les limites non vérifiées sont dans docs/VALIDATION.md.'+s[b:];p.write_text(s,encoding='utf-8')
p=root/'README.md';s=p.read_text(encoding='utf-8').replace('acceptance-v08-release','acceptance-v09-release').replace('verify_distribution.py 0.8.0','verify_distribution.py 0.9.0');p.write_text(s,encoding='utf-8')
print(json.dumps(dict(version='0.9.0',tests=69,images=library['images'],executable_sha256=sha(exe),packages=packages),ensure_ascii=False,indent=2))
