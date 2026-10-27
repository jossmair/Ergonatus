from pathlib import Path
r=Path(__file__).resolve().parents[1]
p=r/'src/ui/dialogs.rs';s=p.read_text(encoding='utf-8').replace('Enregistrez en .ecr ; exportez une copie en PDF, ODT ou DOCX.','Enregistrez en ODT ; exportez une copie en PDF ou DOCX.');p.write_text(s,encoding='utf-8')
p=r/'src/ui/tasks.rs';s=p.read_text(encoding='utf-8').replace('Document trop volumineux pour le format natif (64 Mo).','Document trop volumineux pour un enregistrement complet (64 Mo).');p.write_text(s,encoding='utf-8')
for name in ['ARCHITECTURE.md','DECISIONS.md']:
 p=r/name;s=p.read_text(encoding='utf-8')
 if '## Évolution 0.8.0' not in s:s+='''

## Évolution 0.8.0

Les nouveaux enregistrements utilisent ODT, avec une partie privée Ecrinator/document.json contenant l’enveloppe native versionnée. odt_project.rs compare les CRC/tailles des parties publiques : une modification externe invalide l’ancien état natif et laisse la priorité au contenu ODF. Ce contrôle détecte des changements et ne constitue pas une authentification. Le paquet est écrit neuf en une seule archive finale ; new_append a été écarté après un échec d’ouverture dans LibreOffice 26.2.6.2, reproduit puis corrigé.

odt_design.rs enrichit uniquement notre copie exportée avec un fond de tableau ODF 1.3 et des styles de cellules pour les encadrés. Référence : https://docs.oasis-open.org/office/OpenDocument/v1.3/OpenDocument-v1.3-part3-schema.html (§17.3, §17.15, §17.18). Les textes et tableaux restent éditables dans Writer. Les figures/frises/graphiques ont un PNG de remplacement haute résolution ; les formules gardent MathML. Le modèle natif reste modifiable dans Écrinator à la réouverture de son ODT inchangé. Pagination et polices peuvent différer dans un autre logiciel.

timeline.rs conserve un modèle versionné dans Graphic.app_data et produit des formes/textes vectoriels pour l’éditeur et le PDF. La frise assume un espacement régulier, explicitement indiqué. library.rs lit le catalogue JSON embarqué et des images incluses à la compilation ; aucune requête réseau ne part de l’application. Les téléchargements, auteurs, licences et empreintes sont documentés par fichier. L’image insérée et son crédit forment une seule opération annulable.

Le titre de matière reste du texte Noto Serif gras italique, pour conserver sélection et accessibilité. Le bandeau occupe 100 points. Les contrôles ecr.work-kind constituent un groupe exclusif ; School conserve les trois booléens historiques pour relire les anciens fichiers et les normalise avant sauvegarde.
'''
 p.write_text(s,encoding='utf-8')
p=r/'vendor/wordcraft/ECRINATOR-PATCHES.md';s=p.read_text(encoding='utf-8')
if '## Version 0.8.0' not in s:s+='''

## Version 0.8.0

ContentControl.exclusive_group est optionnel (vide pour les anciens documents). developer.toggleCheckBox met à jour les pairs d’un même groupe dans la même story, vérifie d’abord les verrous puis effectue l’opération en une seule étape annulable. Un groupe ne peut pas rester sans choix ; les cases ordinaires gardent leur comportement amont. Les contrôles scolaires sont testés avec annulation/rétablissement, persistance et classement réel dans Organisator.

Graphic.app_data est une chaîne optionnelle native, absente par défaut. Écrinator y place uniquement son modèle JSON de frise versionné ; les objets Chart/SmartArt amont l’initialisent à None. Les lecteurs DOCX gardent leur comportement. Le remplacement PNG d’une frise en DOCX/ODT est réalisé par les exporteurs à la racine, sans changer le modèle de travail.

Le fond panoramique est maintenant conservé dans la copie ODT par une propriété standard style:background-image, ajoutée à la racine dans odt_design.rs. Les arrondis de tableaux restent propres au natif/PDF. Les contrôles et la géométrie spécifiques restent dans l’état privé de l’ODT, pas dans ses structures publiques ODF.
'''
p.write_text(s,encoding='utf-8')
