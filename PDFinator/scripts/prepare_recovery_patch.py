from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/'release/source-publication-safe'
p=ROOT/'README.md'; t=p.read_text(encoding='utf-8')
for suffix in ['Setup.exe','portable-exe-windows-x64.zip']:
    t=t.replace('releases/download/v1.0.0/PDFinator-1.0.0-'+suffix,'releases/download/v1.0.1/PDFinator-1.0.1-'+suffix)
t=t.replace('Version <strong>1.0.0</strong>','Version <strong>1.0.1</strong>')
t=t.replace('releases/download/v1.0.0/SHA256SUMS.txt','releases/download/v1.0.1/SHA256SUMS.txt')
t=t.replace('**158 tests automatisés réussis** pour la V1','**167 tests automatisés réussis** pour la version 1.0.1')
t=t.replace('[Sources figées de la V1](https://github.com/jossmair/PDFinator/tree/v1.0.0-sources) · [Archive complète des sources](https://github.com/jossmair/PDFinator/releases/download/v1.0.0/PDFinator-1.0.0-sources.zip)',
    '[Sources 1.0.1](https://github.com/jossmair/PDFinator/tree/v1.0.1) · [Archive des sources 1.0.1](https://github.com/jossmair/PDFinator/archive/refs/tags/v1.0.1.zip) · [Anciennes sources V1](https://github.com/jossmair/PDFinator/tree/v1.0.0-sources)')
p.write_bytes(t.encode())
p=ROOT/'CHANGELOG.md'; t=p.read_text(encoding='utf-8')
t=t.replace('## En préparation — récupération complète et contrôles','## 1.0.1 — récupération complète et contrôles')
t=t.replace('Les téléchargements de la V1 ne sont pas remplacés par ce lot de développement.',
    'Les téléchargements 1.0.0 restent disponibles. La version 1.0.1 apporte ces correctifs.\nLes anciens journaux ne contenant que le texte restent lisibles, mais leurs styles\nnon enregistrés ne peuvent pas être reconstruits rétroactivement.')
p.write_bytes(t.encode())
p=ROOT/'assets/banniere.svg'; p.write_bytes(p.read_text(encoding='utf-8').replace('V1.0</text>','V1.0.1</text>').encode())
print('Prepared version 1.0.1 documentation and links.')
