"""Evidence-based product and visual audit. Does not modify application code."""
from pathlib import Path
import ast,html,json,shutil,zipfile,re
from PIL import Image as PI,ImageDraw
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/audit/Ergonatus_Audit_2026-10-19';OUT.mkdir(parents=True,exist_ok=True)
CAP=OUT/'captures';CAP.mkdir(exist_ok=True)
TMP=ROOT/'tmp/pdfs/ergonatus-audit';TMP.mkdir(parents=True,exist_ok=True)
prior=ROOT/'output/presentation/Ergonatus_Presentation_2026-10-19/captures'
for p in prior.glob('*.png'):
    if 'ecrinator' not in p.name and 'pdfinator' not in p.name:shutil.copy2(p,CAP/p.name)

# utility and visual scores are editorial opinions, not clinical or conformance scores.
REVIEWS=[
('Claviernator',5,3,'Très utile pour agir sans clavier physique et personnaliser la saisie.',
 'Touches identifiables, organisation par fonctions, profils de commandes : une base concrète.',
 'Le nom historique Fortinatus et la densité des panneaux rompent l’identité de la suite. Les cibles de clavier doivent rester assez grandes malgré la compacité.',
 'Conserver les touches larges ; simplifier uniquement la configuration. Harmoniser le nom et isoler les réglages avancés.',
 'Tester la saisie dans navigateur, traitement de texte et champs courants, avec souris seule et changements de cible.'),
('Precisionator',5,3,'Un des outils les plus directement liés au confort visuel et à la visée.',
 'Les cinq réglages correspondent à des effets compréhensibles. L’accent violet différencie bien cet outil particulier.',
 'Le fond texturé, les grandes pistes et les valeurs éloignées des libellés alourdissent la lecture. Un thème très sombre ne convient pas à tous.',
 'Proposer un fond uni et un contraste renforcé ; rapprocher valeur et libellé. Garder un aperçu immédiat du réglage.',
 'Vérifier plusieurs niveaux DPI, écrans multiples, déplacement de la loupe et grossissement prolongé.'),
('Transcrinator',5,3,'Gain fort lorsque dicter est plus simple que taper ; le traitement local est un atout.',
 'État Prêt, commande de dictée et rappel du raccourci donnent un point d’entrée clair.',
 'Le visuel central occupe une grande surface sans ajouter de commande. Transcri et Transcrinator coexistent dans les supports.',
 'Réserver l’animation au petit widget ; donner la priorité au microphone, à l’état d’écoute et au résultat. Unifier le nom visible.',
 'Mesurer sur le PC cible les erreurs, la latence, le bruit et le comportement quand la destination de saisie change.'),
('Redactor',5,4,'Assistant de rédaction pertinent si sa fonction reste distincte de la simple correction.',
 'La conversation est lisible ; les bulles différencient brouillon et réponse. Les modes rapides réduisent la saisie.',
 'Le résultat peut être perçu comme une correction certaine. Le bouton de copie est distant de la bulle dans la capture de référence.',
 'Mettre Copier et éventuellement Réutiliser près de chaque réponse. Expliquer clairement Réécrire, Raccourcir et Corriger.',
 'Évaluer fidélité au sens, conservation des faits et annulation sur des textes autres que ceux de démonstration.'),
('Scanator',4,2,'Bon outil passerelle entre papier, capture, lecture et rédaction.',
 'Le texte reconnu reste visible et réutilisable ; l’ouverture d’image et la capture ont des finalités concrètes.',
 'Plusieurs commandes en haut et en bas n’établissent pas un parcours évident. La texture rose concurrence la zone de texte.',
 'Un parcours en trois temps : Choisir ou capturer, Vérifier, Copier ou écouter. Une seule action principale par étape.',
 'Tester colonnes, petites polices, photo inclinée, document bilingue et image de faible contraste.'),
('Organisator',5,3,'Intérêt élevé : créer un espace puis ranger sans suppression répond à un besoin réel.',
 'Les profils, l’aperçu, les propositions et Mes espaces donnent une structure utilisable. L’annulation est un point fort.',
 'Le niveau de confiance du tri ne doit pas être confondu avec une certitude. Beaucoup d’informations et de commandes occupent une seule fenêtre.',
 'Séparer visuellement À vérifier et Prêt à ranger ; montrer source et destination avant déplacement. Garder l’annulation toujours visible.',
 'Tester collisions de noms, fichier modifié, dossier indisponible et annulation. Ne pas promettre une compréhension exhaustive du contenu.'),
('Lector',5,3,'Probablement un des meilleurs points d’entrée de la suite pour lire autrement.',
 'Lecture de sélection et lecture OCR couvrent des situations complémentaires. Femme/Homme et débit sont accessibles.',
 'Les trois gestes de l’Orb demandent de la mémorisation. De gros boutons et un fond lumineux chargé réduisent la sobriété.',
 'Montrer une aide courte au premier usage : clic sélection, clic droit zone, double-clic réglages. Faire ressortir Lire et Arrêter.',
 'Tester sélection réelle, langues OCR, début des mots, périphérique audio et interruption immédiate.'),
('Applinator',4,4,'Utile si le widget reste limité aux applications choisies, sans devenir un deuxième menu Démarrer.',
 'Le widget récent est sobre, compact et centré sur des raccourcis nommés. Le catalogue séparé est une bonne décision.',
 'Certaines icônes gardent une flèche de raccourci ; les icônes inconnues et doublons peuvent dégrader la grille. La sélection initiale doit être évidente.',
 'Extraire des icônes nettes, conserver des noms courts et guider le premier choix de trois à six applications.',
 'Vérifier application désinstallée, cible déplacée, raccourci réseau et réouverture du widget après lancement.'),
('Temporator',4,4,'Le cadran visuel sans chiffres a un intérêt clair pour percevoir le temps sans lire une durée.',
 'Le widget circulaire est un des éléments les plus aboutis visuellement : peu de commandes, fond transparent et état perceptible.',
 'Le test du disque visuel échoue actuellement dans le code source : mauvais argument QPen. Les captures réussies ne prouvent pas que le code présent fonctionne.',
 'Corriger et retester le rendu avant toute nouvelle retouche esthétique. Prévoir un arrêt du clignotement et un mode sans animation.',
 'Rejouer fin, pause, reset, taille et affichage avec/sans chiffres dans la source puis l’exécutable installé.'),
('Concentrator',4,2,'Intérêt simple et défendable : réduire les éléments visibles autour de la tâche.',
 'Le réglage d’assombrissement et le choix de zone correspondent directement au besoin.',
 'La fenêtre de réglages reste décorative alors que la fonction vise justement la réduction des distractions. Le retour à l’affichage normal doit être immédiat.',
 'Une petite barre calme : Choisir la zone, Intensité, Quitter le masque. Garder une sortie clavier et souris très identifiable.',
 'Tester capture multi-écran, résolution différente, accès à la sortie et absence de blocage des applications.'),
('Calculinator',5,3,'Très bon potentiel scolaire : fractions visuelles et calcul symbolique sans choisir un moteur.',
 'La touche = unique, les degrés fixes et le panneau Élève diminuent les décisions. Le pavé souris est pertinent.',
 'La différence entre édition de fraction et expression complète peut rester difficile. Le fond bleu vif, les petits outils et l’historique créent plusieurs densités.',
 'Mettre le champ actif de la fraction en évidence avec une couleur sobre ; stabiliser la hauteur des touches et séparer résultat et saisie.',
 'Faire réaliser à la souris 1/2 + 1/3, une fraction imbriquée et une expression en x ; vérifier les conditions de division.'),
('Communicator',5,2,'Potentiel fort pour communiquer vite, mais il demande une validation avec les personnes et leur vocabulaire.',
 'Message, catégories et cartes offrent un parcours direct ; la lecture des cartes facilite le retour auditif.',
 'La colonne d’émotions est encore construite dans le code et visible dans la capture, malgré la demande de retrait. Dix catégories et beaucoup d’icônes augmentent la charge.',
 'Retirer la colonne non souhaitée ; privilégier quelques catégories et des cartes stables, grandes et lisibles. Choisir une famille cohérente de pictogrammes.',
 'Valider les mots réellement utiles, les cibles de clic et les erreurs de sélection ; un emoji n’est pas à lui seul un pictogramme de communication validé.'),
('Memorinator',4,4,'Usage clair et distinct de l’agenda : garder une idée visible plutôt que planifier un événement.',
 'Couleurs douces, notes datées, déplacement et bandeau unique : le mur est cohérent. La corbeille restaurable est utile.',
 'Le bandeau devient petit sur un grand écran ; la couleur seule ne suffit pas à organiser les notes. Un mur chargé peut perdre sa lisibilité.',
 'Garder le style actuel et ajouter des repères simples de regroupement. Vérifier les contrastes des dates et la taille des icônes.',
 'Tester beaucoup de notes, très longue note, sauvegarde des positions, corbeille et reprise après changement d’écran.'),
('Planinator',5,3,'Cœur organisationnel pertinent, surtout avec l’agenda Élève et le widget du jour.',
 'Glisser sur les jours et matières colorées simplifient l’ajout. Le widget Aujourd’hui/Demain répond à un besoin quotidien.',
 'La grille mensuelle peut afficher peu de contenu par case ; supprimer tout scroll peut cacher l’information au lieu de la rendre accessible. Le fond doré reste très présent.',
 'Garder les semaines ajustées, mais signaler les éléments supplémentaires par +N et proposer le détail du jour. Donner plus d’espace au contenu qu’au décor.',
 'Tester mois chargés, titres longs, sélection de période, fiche au premier plan et conservation du format barré/surligné.'),
('Traductor',4,4,'Conversation bilingue avec écoute locale : une fonction distincte et immédiatement compréhensible.',
 'La présentation SMS, De/Vers et les deux actions dans chaque bulle forment un parcours cohérent.',
 'Le petit modèle local ne permet pas d’inférer une traduction fiable pour tous les textes et toutes les langues. Les icônes audio/copie sont petites.',
 'Agrandir les cibles sans agrandir les pictogrammes ; rendre le chargement et la langue lue explicites. Garder une mise en garde courte pour les textes sensibles.',
 'Évaluer séparément chaque langue, les nombres, négations, noms propres et la qualité acoustique perçue.'),
('Corrector',5,3,'Le remplacement d’une sélection est un usage fort, plus direct qu’un échange avec un assistant.',
 'Original/Résultat, restauration sous conditions et sablier répondent aux étapes de correction et d’attente.',
 'La promesse zéro faute serait excessive. La fenêtre conserve plusieurs gros boutons et un fond très détaillé. Le remplacement dépend du champ cible.',
 'Une hiérarchie nette : Corriger, résultat, Copier ou Remplacer si disponible. Montrer clairement ce qui n’a pas pu être vérifié.',
 'Constituer un corpus de fautes inédites ; tester navigateur, bureautique, champs protégés, annulation et restauration sans écraser une saisie nouvelle.'),
]

FINDINGS=[
('P1','Écrinator et PDFinator sont encore présentés comme livrés',
 'La demande utilisateur les déclare non développés. Le catalogue et le lanceur gardent pourtant leurs entrées, exécutables et captures. Le résumé précédent les décrivait comme des fonctions disponibles.',
 'Afficher À développer, désactiver le lancement de ces deux entrées ou les placer dans une zone À venir. Corriger la documentation et les profils si nécessaire.',
 'shared/ui/theme.py ; Hub/fort_hub.py:SuiteLauncher.rebuild ; correction de périmètre utilisateur.'),
('P1','Erreur reproductible du cadran visuel',
 'Le test test_visual_disc_shrinks_and_preserves_running_timer échoue : Qt.RoundJoin est passé à la place d’un PenCapStyle dans QPen.',
 'Passer explicitement cap et jointure dans le bon ordre, puis reconstruire et vérifier le binaire. Aucune correction de code n’est faite dans cet audit.',
 'shared/apps/timer_widget.py:78 ; .audit-targeted.log ; 39 tests passent et 1 échoue.'),
('P1','La sortie de toute la suite n’est pas complètement démontrée',
 'Les satellites reçoivent quit par IPC ; quatre outils historiques reçoivent WM_QUIT. Il n’y a pas d’accusé de sortie ni d’attente d’arrêt. Le code ne gère pas explicitement ici le cycle de vie des moteurs partagés.',
 'Utiliser les chemins de sortie applicatifs qui sauvegardent, puis vérifier la disparition des processus et le comportement des moteurs. Tester avec un document en cours et une tâche IA.',
 'shared/catalog.py:quit_suite ; tests/test_hub_suite_quit.py simule le routage Windows, pas une sauvegarde réelle des quatre outils.'),
('P2','Un interrupteur éteint peut laisser le logiciel actif',
 'toggle_active(False) retire la sélection et masque l’Orb, sans appeler stop. L’utilisateur peut lire ce bouton comme un arrêt du logiciel.',
 'Distinguer Sélectionné au lancement, Afficher l’Orb et Arrêter. Préférer une case de sélection si le bouton ne représente pas un état marche/arrêt.',
 'Hub/fort_hub.py:toggle_active.'),
('P2','Avec Windows a une sémantique surprenante',
 'Au lancement --startup, la liste du profil actif est réunie avec startup_apps. Une application cochée dans le profil peut donc démarrer avec Windows même si sa case Avec Windows est décochée, dès lors que le hub démarre.',
 'Clarifier : un réglage global Lancer Ergonatus avec Windows et une sélection Au lancement du hub, ou respecter strictement une sélection Windows distincte.',
 'run_ergonatus.py:schedule_startup ; Hub/fort_hub.py:launch_selected_on_startup ; shared/startup.py.'),
('P2','Le focus clavier des interrupteurs n’est plus visible',
 'Le cadre bleu a été retiré par border:none et outline:none sur :focus, sans indicateur de remplacement. Le nom accessible existe mais ne remplace pas le repère visuel.',
 'Ajouter un halo discret, un soulignement ou un changement de contraste au focus, sans réintroduire le cadre bleu rejeté.',
 'Hub/fort_hub.py:STYLE, QCheckBox#Switch:focus.'),
('P2','La colonne émotions demandée en retrait subsiste',
 'QuickEmotions est encore ajouté à la ligne du tableau de Communicator ; la capture retenue la montre aussi.',
 'Retirer cette colonne du parcours principal puis recalculer les cartes sur la largeur récupérée.',
 'shared/apps/communication.py:97-101 ; capture 17-communicator.png.'),
('P2','Les anciens réglages sont conservés mais leur accès visible a disparu',
 'Le bouton Options a été retiré comme demandé ; les pages avancées continuent d’être construites. Certains réglages et états détaillés y restent isolés.',
 'Faire l’inventaire des réglages indispensables et conserver seulement un accès clairement nommé à ceux qui restent nécessaires, avec accord produit.',
 'Hub/fort_hub.py:build/show_options ; Hub/window.py:build.'),
]

PAGES=[]
def page(title,lead,blocks,images=(),tag='AUDIT PRODUIT ET VISUEL'):
    PAGES.append(dict(title=title,lead=lead,blocks=blocks,images=list(images),tag=tag))
page('Une bonne idée, encore inégale','Verdict : un intérêt réel, mais pas encore une suite visuellement et fonctionnellement homogène.',[
 ('Ce qui justifie la suite','Le hub et les Orbs rapprochent des fonctions utiles qui évitent de passer sans cesse d’un menu à l’autre : lire, dicter, corriger, organiser et percevoir le temps. Les profils donnent une porte d’entrée compréhensible.'),
 ('Ce qui freine son adoption','La sélection, l’ouverture, le masquage et l’arrêt ne sont pas toujours distingués. Les fenêtres ont des niveaux de finition différents. Les fonds décoratifs concurrencent parfois les tâches.'),
 ('Périmètre corrigé','16 applications dans le périmètre produit à examiner, de maturités différentes. Écrinator et PDFinator sont non développés et exclus des notes. Les 18 tuiles visibles ne prouvent pas 18 produits achevés.'),
 ('Priorité','Stabiliser les parcours et les états avant de multiplier les fonctions ou les images. Le style cible devrait prolonger la sobriété des meilleurs widgets récents.')],['02-lanceur-opacite.png'])
page('Méthode et niveau de preuve','Un audit de l’existant, pas une certification ni une campagne utilisateurs.',[
 ('Revue visuelle','27 captures de référence examinées ; 25 conservées ici après exclusion des deux produits non développés. Elles proviennent de phases de validation différentes. Les constats visuels portent sur ces rendus, pas sur toutes les fenêtres actuelles.'),
 ('Revue de code','Catalogue, hub, démarrage, fermeture groupée, widgets, outils de communication et règles de focus. Les chemins et fonctions importants sont indiqués dans les constats.'),
 ('Tests relancés','40 tests ciblés : Temporator, Communicator, démarrage du hub et routage de fermeture. Résultat : 39 réussis, 1 échec de peinture du disque visuel. Journal joint dans preuves.'),
 ('Ce qui reste à mesurer','Pas de panel DYS/handicap, de mesure clinique, de conformité WCAG/RGAA, de benchmark global de latence/RAM, ni de test matériel multi-écrans complet. Pas de garantie sur les textes arbitraires de l’IA.'),
 ('Les notes','Notes éditoriales sur 5 : intérêt potentiel dans un usage adapté et qualité visuelle des captures. Elles ne mesurent ni l’efficacité clinique ni la maturité technique.')])
page('Où se trouve la valeur ?','L’intérêt vient du parcours complet et de l’accès rapide, pas du nombre de logiciels.',[
 ('Écrire et relire','Claviernator ou Transcrinator pour produire ; Corrector pour corriger une sélection ; Redactor pour reformuler ; Lector pour vérifier à l’oreille. Les rôles doivent rester très distincts.'),
 ('Lire et comprendre','Scanator transforme des pixels en texte ; Lector le restitue oralement ; Traductor change de langue. Montrer une continuité entre ces outils aurait plus de valeur que de nouvelles fenêtres isolées.'),
 ('Apprendre et s’organiser','Calculinator, Planinator, Temporator et Memorinator apportent des supports concrets. Organisator gère les fichiers ; Applinator réduit le détour pour ouvrir une application.'),
 ('Adapter plutôt que promettre','Les profils sont des présélections modifiables. Les intitulés DYS, moteur ou déficience visuelle ne garantissent pas que l’interface convient à toutes les personnes concernées.'),
 ('Risque de dispersion','Une personne n’a pas besoin de 16 Orbs actives. Commencer par trois à cinq outils et laisser découvrir le reste peut réduire la charge d’apprentissage.')])
page('Lecture des notes','Un niveau élevé d’intérêt peut coexister avec une interface encore faible.',[
 ('Application   /   Intérêt   /   Visuel','\n'.join(f'{n}   /   {u}/5   /   {v}/5' for n,u,v,*_ in REVIEWS)),
 ('Interprétation','5 = fort potentiel ou rendu très abouti ; 3 = utile mais perfectible ; 1 = faible dans le contexte observé. Aucun score visuel 5 n’est attribué : la cohérence de suite et l’accessibilité restent à démontrer.'),
 ('Hors notation','Écrinator et PDFinator : non développés. Leur présence dans les captures précédentes ne doit plus être présentée comme une livraison.')])
page('Bilan visuel : le hub','La structure est meilleure que le décor ; la lisibilité doit commander le style.',[
 ('À garder','Liste claire, profils, état de chaque logiciel, aide ?, taille compacte et nouvelle teinte des interrupteurs. Le panneau des tuiles est plus calme que la majorité des fenêtres satellites.'),
 ('À améliorer','Les intitulés de sélection ne séparent pas suffisamment démarrage et état réel. Les deux produits à venir doivent être identifiés. La longue liste nécessite un choix de favoris ou de catégories.'),
 ('Orb et identité','La sphère bleue est reconnaissable à grande taille, mais les détails métalliques se perdent à 36 px. Tester une silhouette simplifiée et conserver le nom dans une infobulle ; ne pas générer un nouvel effet décoratif avant cela.')],['01-hub.png'])
page('Bilan visuel : la rupture de style','Deux directions coexistent : fenêtres spectaculaires et widgets apaisés.',[
 ('Constat','Scanator, Lector, Corrector et plusieurs réglages utilisent encore des textures très contrastées et de gros boutons. Applinator, le mur de notes et le cadran montrent une direction plus sobre.'),
 ('Conséquence','La couleur aide à reconnaître un outil ; une texture brillante derrière du texte ajoute du bruit. Le sentiment premium ne dépend pas d’un nombre élevé d’effets lumineux.'),
 ('Direction recommandée','Fond uni ou texture presque imperceptible ; une couleur d’accent par logiciel ; typographie commune ; espacements réguliers ; tailles de boutons liées à leur usage, pas uniformément petites.')],['11-lector.png','12-applinator.png'])
page('Un système visuel commun','Des règles répétées permettent de comprendre un nouvel outil plus vite.',[
 ('Typographie','Une famille principale ; trois niveaux visibles : titre, contenu, aide. Ne pas réduire les textes pour supprimer toutes les barres de défilement.'),
 ('Couleurs','Réserver l’accent aux actions et états. Utiliser aussi des mots et des icônes : la couleur seule ne doit pas signifier activé, matière ou erreur.'),
 ('Boutons et icônes','Une action principale par étape. Écouter, Copier, Supprimer et Réinitialiser gardent la même forme et la même place d’un logiciel à l’autre. Éviter le mélange emoji, symboles texte, icônes détaillées et vecteurs sans règle.'),
 ('Cibles de clic','Petite icône ne signifie pas petite zone de clic. Viser des zones confortables, plus grandes dans les profils moteurs, et vérifier qu’elles ne se chevauchent pas.'),
 ('Transparence','Fond réglable, contenu opaque. Fournir une valeur par défaut suffisamment sombre et tester sur un bureau chargé et une fenêtre blanche.'),
 ('Animations','Utiles pour attente, écoute et fin de minuteur. Prévoir une réduction des animations et une façon d’arrêter le clignotement.')])
page('États et commandes : les écarts','Les comportements doivent être aussi cohérents que les couleurs.',[(f'{p} - {title}',body+' Recommandation : '+fix+' Preuve : '+proof) for p,title,body,fix,proof in FINDINGS[3:6]])
page('Confiance et cycle de vie','Fermer, sauvegarder et retrouver doivent être démontrés, pas seulement annoncés.',[(f'{p} - {title}',body+' Recommandation : '+fix+' Preuve : '+proof) for p,title,body,fix,proof in FINDINGS[:3]])
page('Accessibilité : déjà des bases','Les profils adaptés ne remplacent pas des essais avec les personnes concernées.',[
 ('Points positifs','De nombreux contrôles portent un nom accessible ; les widgets prévoient des raccourcis et des gestes souris. Des réglages de voix, taille et transparence existent.'),
 ('Point confirmé','Le focus des interrupteurs du hub a été supprimé sans alternative visible. Il faut un repère discret, même lorsque le cadre bleu n’est plus souhaité.'),
 ('À vérifier en usage réel','Ordre Tab, lecteur d’écran, contraste texte/fond, mode clair, grossissement Windows, cibles pour précision réduite, sortie d’un voile plein écran et accès à toutes les commandes sans double-clic.'),
 ('Charge cognitive','Un clic, double-clic et clic droit différents selon l’outil peuvent être efficaces après apprentissage mais difficiles à découvrir. Afficher une aide au premier usage, puis laisser la masquer.'),
 ('Règle produit','Ne pas rendre les boutons plus petits par principe. Réduire le décor et les marges inutiles avant de réduire les cibles nécessaires à l’interaction.')])
for i,(name,u,v,interest,strong,weak,action,verify) in enumerate(REVIEWS):
    capture=next(p.name for p in CAP.glob('*.png') if p.stem[3:]==name.lower().replace('é','e'))
    page(name,f'Intérêt {u}/5 · Visuel {v}/5 · Appréciation éditoriale, pas une certification.',[
        ('Intérêt',interest),('Ce qui fonctionne',strong),('Ce qui freine',weak),('Amélioration prioritaire',action),('Validation à prévoir',verify)],
        [capture],tag=f'FICHE {i+1:02d} / 16')
page('Écrinator et PDFinator','Non développés : à sortir du périmètre livré et des promesses actuelles.',[
 ('Correction du bilan précédent','Le résumé précédent a décrit ces deux outils à partir d’ébauches et de captures. Cette présentation était trop affirmative. Leur statut produit est désormais non développé ; ils ne sont pas notés dans cet audit.'),
 ('Écrinator : décider du rôle avant de construire','L’espace d’écriture n’a un intérêt propre que s’il apporte une simplicité ou une adaptation que Redactor et un traitement de texte ne couvrent pas. Définir le public, la tâche centrale et ce qui est volontairement absent.'),
 ('PDFinator : partir du besoin de document','Priorité potentielle : lire un énoncé, écouter le texte, surligner, annoter et remplir. Distinguer PDF texte, scan et formulaire. Ne pas promettre un éditeur PDF généraliste.'),
 ('Affichage recommandé maintenant','Deux cartes À venir, sans bouton de lancement ni inclusion dans les sélections automatiques. Aucune capture d’ébauche ne doit être utilisée comme preuve d’un logiciel terminé.'),
 ('Critère de lancement du développement','Stabiliser les parcours et les défauts confirmés de la suite actuelle, puis valider le besoin avec quelques tâches représentatives.')])
page('Priorités de travail','Stabiliser d’abord ; harmoniser ensuite ; étendre en dernier.',[
 ('P1 - Avant d’annoncer une suite finalisée','Marquer Écrinator/PDFinator À développer. Corriger le défaut de peinture Temporator. Vérifier la fermeture et la sauvegarde réelles des outils et le devenir des moteurs partagés.'),
 ('P2 - Lever les ambiguïtés','Clarifier Sélectionné / Ouvert / Orb masquée / Arrêté et le sens de Avec Windows. Rétablir le focus clavier discret. Retirer la colonne émotions non souhaitée. Répertorier les réglages devenus inaccessibles.'),
 ('P2 - Harmoniser les parcours fréquents','Alléger les fonds et les gros boutons sans réduire les cibles utiles. Partager les icônes Copier/Écouter. Mettre les actions au contact du contenu.'),
 ('P3 - Approfondir la valeur','Favoris ou groupes dans le hub, aide de première utilisation, parcours OCR vers lecture et rédaction. Évaluer chaque profil sur de vraies tâches.'),
 ('Plus tard','Développer les deux applications en attente une fois leurs rôles définis. Ne pas ajouter de nouvelles fonctions pour compenser un problème de clarté.')])
page('Comment savoir que c’est prêt ?','Une liste de critères observables plutôt qu’une appréciation vague.',[
 ('Parcours de base','Un nouveau profil se prépare, se lance et se retrouve après redémarrage. Les états affichés correspondent aux processus. Les deux outils à venir ne démarrent pas.'),
 ('Sans surprise','Masquer ne perd pas une saisie. Quitter laisse les données sauvegardées et aucun processus inattendu. Une erreur montre comment reprendre.'),
 ('Visuel','Les textes se lisent à 100 %, 150 % et 200 % Windows ; pas de commandes coupées. La transparence ne baisse pas le contraste des cartes. Les boutons gardent un focus visible.'),
 ('Souris et clavier','Toutes les tâches centrales se font à la souris, mais aussi avec un ordre clavier prévisible. Les zones de clic sont essayées avec précision réduite.'),
 ('IA et audio','Le corpus de correction/traduction contient des cas nouveaux. Les limites restent explicites. Lecture, annulation, chargement et changement de périphérique sont vérifiés.'),
 ('Panel représentatif','Quelques utilisateurs du public visé réalisent des tâches sans aide continue. Relever les erreurs, le besoin d’explication et la fatigue plutôt que seulement une préférence esthétique.')])
page('Preuves et limites du bilan','Les constats sont traçables ; les inconnues restent indiquées.',[
 ('Résultat exécuté pour cet audit','39 tests passent ; 1 échoue dans test_temporator.py, sur test_visual_disc_shrinks_and_preserves_running_timer. Le journal complet est joint sous preuves/audit-tests.log. Les fonctions applicatives n’ont pas été modifiées.'),
 ('Résultats antérieurs','Les rapports de démarrage compilé du hub et d’Écrinator, et de fermeture d’un satellite isolé existent. Le test utilisant Écrinator vérifie un mécanisme du hub ; il ne valide pas ce produit comme développé.'),
 ('Sources internes','Hub/fort_hub.py ; Hub/window.py ; run_ergonatus.py ; shared/catalog.py ; shared/startup.py ; shared/ui/window_behavior.py ; shared/apps/communication.py ; shared/apps/timer_widget.py ; tests et rapports docs/validation.'),
 ('Visuels','Captures déjà produites pendant le développement, avec leurs variantes et noms historiques. Le manifeste des images et les sources des constats sont joints. Aucun test utilisateur, aucune mesure de contraste systématique ni nouvelle validation audio globale n’a été réalisé.'),
 ('Conclusion','Le socle peut être utile et reconnaissable. Le prochain gain ne viendra pas d’un décor plus spectaculaire : il viendra d’états fiables, de parcours plus simples et d’une finition commune aux applications déjà dans le périmètre.')])

for n,f in [('S','segoeui.ttf'),('SB','segoeuib.ttf')]:pdfmetrics.registerFont(TTFont(n,str(Path('C:/Windows/Fonts')/f)))
pdf=OUT/'Ergonatus_Audit_interet_et_bilan_visuel.pdf'
c=canvas.Canvas(str(pdf),pagesize=(595.276,841.89));c.setTitle('Ergonatus - Audit, intérêt et bilan visuel');c.setAuthor('Audit Ergonatus')
def para(text,x,y,w=499,size=10,color='#24384D',bold=False):
    text=html.escape(text).replace('\n','<br/>')
    p=Paragraph(text,ParagraphStyle('p',fontName='SB' if bold else 'S',fontSize=size,leading=size*1.38,textColor=HexColor(color)))
    _,h=p.wrap(w,1200);p.drawOn(c,x,y-h);return y-h-8
metrics=[]
for num,p in enumerate(PAGES,1):
    c.bookmarkPage(f'page-{num}');c.addOutlineEntry(p['title'],f'page-{num}',level=0,closed=False)
    c.setFillColor(HexColor('#F5F8FC'));c.rect(0,0,596,842,fill=1,stroke=0)
    c.setFillColor(HexColor('#152840'));c.rect(0,709,596,133,fill=1,stroke=0)
    para(p['tag'],48,811,size=8,color='#8EC8D7',bold=True)
    para(p['title'],48,785,size=23,color='#FFFFFF',bold=True)
    c.setFont('S',8);c.setFillColor(HexColor('#627991'));c.drawString(48,28,'ERGONATUS  /  AUDIT DU 19 OCTOBRE 2026');c.drawRightString(548,28,f'{num:02d}')
    y=para(p['lead'],48,686,size=11.3,bold=True)-5
    # Dense pages reduce text slightly; app pages leave their lower area for the screenshot.
    size=9.2 if len(p['blocks'])<=5 and len(''.join(t for _,t in p['blocks']))>1500 else 10
    if num==4:size=10.5
    for title,text in p['blocks']:
        y=para(title,48,y,size=size+0.4,bold=True)
        y=para(text,48,y,size=size)
    if p['images']:
        top=y-9;bottom=77;totalw=499;gap=12;count=len(p['images']);slot=(totalw-gap*(count-1))/count
        assert top-bottom>100,(num,top)
        for i,name in enumerate(p['images']):
            path=CAP/name
            with PI.open(path) as im:iw,ih=im.size
            factor=min(slot/iw,(top-bottom-17)/ih);w,h=iw*factor,ih*factor;x=48+i*(slot+gap)+(slot-w)/2
            c.setFillColor(HexColor('#E1E8EF'));c.roundRect(x-3,top-h-3,w+6,h+6,6,fill=1,stroke=0)
            c.drawImage(ImageReader(str(path)),x,top-h,w,h,mask='auto')
        para('Capture de référence - le rendu observé ne prouve pas la maturité fonctionnelle.',48,bottom-6,size=7.5,color='#657A91')
    else:assert y>52,(num,y)
    metrics.append({'page':num,'title':p['title'],'text_bottom':round(y,1)})
    c.showPage()
c.save()

def esc(t):return html.escape(t)
sections=[]
for i,p in enumerate(PAGES,1):
    blocks=''.join('<h3>'+esc(title)+'</h3><p>'+esc(text).replace('\n','<br>')+'</p>' for title,text in p['blocks'])
    imgs=''.join(f'<figure><a href="captures/{name}"><img loading="lazy" src="captures/{name}" alt="Capture de référence"></a><figcaption>Capture de référence, pas une preuve de produit finalisé.</figcaption></figure>' for name in p['images'])
    sections.append(f'<section id="p{i}"><small>{esc(p["tag"])}</small><h2>{esc(p["title"])}</h2><p class="lead">{esc(p["lead"])}</p>{blocks}<div class="images">{imgs}</div></section>')
css='''body{background:#0d1726;color:#dae6f3;font:17px/1.65 "Segoe UI",Arial;margin:0}main{max-width:1100px;margin:auto;padding:35px}h1{font-size:52px}h2{font-size:31px;color:white}h3{color:#9bd0de;margin-bottom:4px}p{margin-top:4px}.lead{font-size:21px;color:#b9d7e5}section{padding:30px;background:#17283e;border:1px solid #304964;border-radius:22px;margin:30px 0}small{color:#7fb6c8;letter-spacing:2px}a{color:#a9dbe7}nav a{display:inline-block;padding:6px 12px}.images{display:flex;gap:15px;align-items:start}figure{flex:1;min-width:0;margin:20px 0}img{max-width:100%;max-height:650px;display:block;margin:auto;object-fit:contain;border-radius:9px}figcaption{font-size:12px;color:#a0b2c7}@media(max-width:650px){main{padding:15px}section{padding:20px}.images{display:block}h1{font-size:37px}}'''
nav=''.join(f'<a href="#p{i}">{esc(p["title"])}</a>' for i,p in enumerate(PAGES,1))
(OUT/'Ouvrir_audit.html').write_text('<!doctype html><html lang="fr"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Ergonatus - Audit</title><style>'+css+'</style><main><h1>Audit Ergonatus</h1><p class="lead">Intérêt, bilan visuel et priorités. 16 outils examinés ; Écrinator et PDFinator non développés.</p><nav>'+nav+'</nav>'+''.join(sections)+'</main></html>',encoding='utf-8')
txt=['AUDIT ERGONATUS - 19 OCTOBRE 2026','16 outils examinés. Écrinator et PDFinator non développés.']
for p in PAGES:
    txt+=['',p['title'].upper(),p['lead']]
    for title,body in p['blocks']:txt += ['',title,body]
(OUT/'Audit_complet.txt').write_text('\n'.join(txt),encoding='utf-8')
(OUT/'Constats_priorises.json').write_text(json.dumps([dict(priority=p,title=t,observation=o,recommendation=r,evidence=e) for p,t,o,r,e in FINDINGS],ensure_ascii=False,indent=2),encoding='utf-8')
proof=OUT/'preuves';proof.mkdir(exist_ok=True)
shutil.copy2(ROOT/'.audit-targeted.log',proof/'audit-tests.log')
for file in ['ergonatus-startup-smoke.json','ergonatus-updated-smoke.json']:shutil.copy2(ROOT/'docs/validation'/file,proof/file)
(OUT/'LISEZ-MOI.txt').write_text('AUDIT ERGONATUS\n\nExtraire le ZIP, puis ouvrir le PDF ou Ouvrir_audit.html.\nLe texte seul et les constats prioritaires sont joints.\n\nPérimètre corrigé : 16 outils examinés ; Écrinator et PDFinator non développés.\nLes captures sont des références de développement, pas des garanties de livraison.\n39 tests ciblés passent ; 1 échec confirmé sur le disque visuel de Temporator.\nAucun code applicatif modifié dans cet audit.\n',encoding='utf-8')
(OUT/'CORRECTION_DU_RESUME_PRECEDENT.txt').write_text('Le ZIP de présentation précédent décrivait trop affirmativement Écrinator et PDFinator à partir d’ébauches présentes dans le dossier.\nCes deux logiciels sont NON DÉVELOPPÉS selon le périmètre produit confirmé par l’utilisateur.\nIls sont exclus de la notation et du périmètre livré de cet audit. La présence d’une capture ou d’un exécutable ne change pas ce statut.\n',encoding='utf-8')
pages=PdfReader(pdf).pages;assert len(pages)==len(PAGES)
for i,p in enumerate(pages):assert len(p.extract_text() or '')>200,i
(TMP/'layout.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'pages':len(pages),'captures':len(list(CAP.glob('*.png'))),'report':str(pdf)},ensure_ascii=False))
