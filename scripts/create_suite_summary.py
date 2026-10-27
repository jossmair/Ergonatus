"""Build an offline illustrated presentation, without packaging user data or binaries."""
from pathlib import Path
import html,json,shutil,zipfile,hashlib
from PIL import Image as PILImage,ImageOps,ImageDraw
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/presentation/Ergonatus_Presentation_2026-10-19'
OUT.mkdir(parents=True,exist_ok=True);(OUT/'captures').mkdir(exist_ok=True)
TMP=ROOT/'tmp/pdfs/ergonatus-summary';TMP.mkdir(parents=True,exist_ok=True)

# name, role, capabilities, first-use instruction, practical boundary, screenshot
APPS=[
('Claviernator','Saisir et piloter à la souris',
 ['Clavier virtuel et touches adaptées.','Profils de commandes, actions de souris et défilement.','Orb dédiée avec commandes de défilement.'],
 'Ouvrir le clavier depuis son Orb, placer le curseur dans le champ cible, puis cliquer sur les touches.',
 'La compatibilité de saisie dépend du champ et des droits de l’application cible.',
 'Claviernator/source/docs/validation/clavier-compact.png'),
('Precisionator','Agrandir et viser plus facilement',
 ['Loupe dynamique autour de la zone visée.','Grossissement et taille de loupe réglables.','Réglages du délai de visée et de la vitesse de souris.'],
 'Activer la loupe puis ajuster le grossissement et le confort de visée dans la fenêtre.',
 'Le rendu dépend de la capture écran et de la configuration d’affichage Windows.',
 'Precisionator/source/docs/validation/parametres-natifs-1.0.7.png'),
('Transcrinator','Dicter plutôt que taper',
 ['Reconnaissance vocale locale.','Dictionnaire et réglages de transcription.','Insertion dans une application compatible ou conservation du texte dans l’outil.'],
 'Choisir le microphone et le raccourci, démarrer la dictée, parler puis arrêter pour obtenir le texte.',
 'Le microphone, le bruit ambiant et la langue influencent la transcription. Certaines captures portent le nom historique Transcri.',
 'Transcrinator/source/docs/validation/home-premium.png'),
('Redactor','Rédiger et reformuler',
 ['Assistant de rédaction local, présenté en conversation.','Modes de formulation : naturel, mail et court.','Réponse copiable pour la réutiliser dans un autre logiciel.'],
 'Saisir une demande ou un brouillon, choisir le ton, puis copier la réponse utile.',
 'Relire les propositions ; une génération peut modifier une nuance ou produire une information inexacte.',
 'Redactor/source/docs/validation/redactor-resultat.png'),
('Scanator','Récupérer le texte d’une image',
 ['Reconnaissance de texte à partir d’une capture ou d’une image.','Aperçu et récupération du texte reconnu.','Texte copiable et réutilisable dans les autres outils.'],
 'Capturer une zone ou ouvrir une image, lancer la reconnaissance, puis vérifier et copier le texte.',
 'La qualité dépend du contraste, de la résolution et des langues de reconnaissance disponibles.',
 'docs/validation/scanator-streamlined.png'),
('Écrinator','Écrire dans un espace simple',
 ['Zone de rédaction dépouillée.','Saisie et réutilisation du texte.','Accès rapide depuis le hub et son Orb.'],
 'Ouvrir l’outil, écrire son texte puis le copier pour l’utiliser ailleurs.',
 'Cet outil est un espace d’écriture ; il ne remplace pas un traitement de texte complet.',
 'docs/validation/ecrinator-packaged.png'),
('Organisator','Ranger ses documents dans des espaces',
 ['Création sur le Bureau : École primaire, Collège, Professionnel ou Particulier.','Sous-dossiers et icônes colorées, aperçu des fichiers et propositions de rangement.','Déplacements sans suppression ni écrasement ; annulation du dernier lot sous conditions.','Mes espaces retrouve les espaces créés ou ouverts ; rangement automatique optionnel.'],
 'Créer un espace, y déposer les fichiers, vérifier les propositions puis utiliser Ranger les fichiers sélectionnés.',
 'Le classement repose sur des règles locales et des indices de contenu ; les cas ambigus restent à vérifier.',
 'docs/validation/organisator-clarity.png'),
('Lector','Écouter un texte ou une zone de l’écran',
 ['Voix locales Femme et Homme, avec réglage du débit.','Clic Orb : sélectionner un texte pour le lire.','Clic droit Orb : tracer une zone pour reconnaissance et lecture.','Double-clic : ouvrir les réglages ; sablier pendant la préparation.'],
 'Cliquer sur l’Orb puis sélectionner un passage, ou utiliser la lecture d’une zone pour une image.',
 'Une sélection inaccessible à Windows peut nécessiter la capture OCR ; celle-ci dépend de la lisibilité.',
 'docs/validation/lector-compact.png'),
('Applinator','Retrouver ses applications favorites',
 ['Détection des applications installées et catalogue filtré.','Sélection des raccourcis dans l’application, puis affichage dans le widget.','Lancement en un clic ; fermeture du widget par l’Orb ou le fond.','Fond du widget réglable et raccourcis mémorisés.'],
 'Cocher les applications utiles dans la fenêtre ; cliquer ensuite sur l’Orb pour retrouver uniquement ces raccourcis.',
 'Un raccourci dont la cible a été déplacée ou désinstallée doit être mis à jour.',
 'docs/validation/applinator-polished-widget.png'),
('Temporator','Voir le temps qui reste',
 ['Minuteur à cadran, avec chiffres ou disque visuel sans chiffres.','Réglage à la souris, durées rapides et taille du widget ajustable.','Fond transparent autour du cadran ; démarrage et remise à zéro par icônes.','Fin clignotante ; clic Orb pour afficher ou masquer, sans notification Windows.'],
 'Choisir la durée, lancer le minuteur puis utiliser son petit cadran pendant le travail.',
 'Le minuteur fonctionne tant que son processus reste ouvert. Les captures présentent les variantes du cadran.',
 'docs/validation/temporator-polished-visual.png'),
('Concentrator','Mettre une zone de travail en évidence',
 ['Sélection d’une zone à conserver visible.','Assombrissement de ce qui l’entoure.','Retour rapide à l’affichage habituel.'],
 'Définir la zone de lecture ou de travail, puis quitter le masque une fois l’activité terminée.',
 'Il s’agit d’une aide visuelle ; le contenu de la zone n’est pas transformé.',
 'docs/validation/concentrator-compact.png'),
('PDFinator','Lire et annoter un PDF',
 ['Ouverture et navigation dans les pages.','Ajout de notes et remplissage des champs texte pris en charge.','Sauvegarde dans une copie du document original.'],
 'Ouvrir le PDF, naviguer, annoter ou remplir les champs puis enregistrer une copie.',
 'Les fonctions prises en charge ne couvrent pas toute l’édition avancée de PDF.',
 'docs/validation/pdfinator-packaged.png'),
('Calculinator','Calculer simplement, y compris au collège',
 ['Pavé numérique utilisable à la souris et historique.','Mode Élève : x, x², y, y², racine, pi, sin, cos et tan.','Fractions à barre horizontale, saisies dans l’écran principal.','La touche = calcule, développe et simplifie automatiquement ; angles toujours en degrés.'],
 'Activer Mode Élève si besoin ; pour une fraction, cliquer sur a/b puis remplir le haut et le bas avec les touches.',
 'Pas de résolution d’équations ni de démonstration étape par étape ; les domaines de validité restent importants.',
 'docs/validation/calculinator-modern-student.png'),
('Communicator','S’exprimer avec des cartes',
 ['Cartes de communication et pictogrammes.','Catégories Essentiels, École, Besoins, Ressentis et Favoris.','Zone de message et écoute des éléments selon les commandes disponibles.'],
 'Choisir une catégorie, cliquer sur les cartes utiles et utiliser la zone de message pour compléter.',
 'Le vocabulaire des cartes et les voix disponibles doivent correspondre aux besoins de l’utilisateur.',
 'docs/validation/communicator-compact-v2.png'),
('Memorinator','Garder ses idées sur un mur de post-it',
 ['Notes colorées, datées et déplaçables.','Gros + pour ajouter, icône poubelle pour retirer une note.','Surlignage et texte barré via des icônes.','Notes qui grandissent avec leur contenu et fond à opacité réglable.'],
 'Afficher le mur depuis l’Orb, ajouter une note, écrire puis déplacer les post-it pour organiser ses idées.',
 'Le mur sert aux notes locales ; il ne remplace pas un agenda ou une synchronisation entre appareils.',
 'docs/validation/memorinator-single-row.png'),
('Planinator','Organiser ses journées et sa semaine',
 ['Agenda Jour, Semaine et Mois, avec mois ajusté à 4, 5 ou 6 semaines.','Sélection de plusieurs jours par glissement et création directe d’une fiche.','Mode Élève : matières sélectionnables et couleurs automatiques.','Surlignage et barré ; widget Aujourd’hui et Demain à fond réglable.'],
 'Clic Orb : widget quotidien. Double-clic : agenda. Cliquer sur un jour pour ajouter ; glisser pour une période.',
 'Données locales : pas de synchronisation Google Agenda, de récurrence ou d’import scolaire dans cette version.',
 'docs/validation/planinator-school-month.png'),
('Traductor','Échanger dans une autre langue',
 ['Conversation de type SMS : source à gauche, traduction à droite.','Langue de départ, langue de sortie et inversion en haut.','Chaque bulle possède Écouter et Copier.','Huit langues avec voix locales : français, anglais, espagnol, allemand, italien, portugais, arabe et ukrainien.'],
 'Choisir les deux langues, écrire et envoyer ; écouter ou copier la bulle traduite.',
 'La qualité varie selon les langues et les textes. Le chargement initial d’un modèle peut demander quelques secondes.',
 'docs/validation/traductor-reversed-bubbles.png'),
('Corrector','Corriger un passage sans le ressaisir',
 ['Correction locale de l’orthographe, de la grammaire et de la ponctuation.','Clic Orb : sélectionner un passage ; remplacement si la cible est encore vérifiable.','Double-clic : fenêtre Original / Résultat, copie et restauration sous conditions.','Sablier animé pendant le traitement ; ponctuation finale ajoutée si nécessaire au-delà de cinq mots.'],
 'Cliquer sur l’Orb, sélectionner le passage, attendre la proposition ; utiliser Copier si le remplacement n’est pas possible.',
 'Aucune garantie universelle de zéro faute. Les champs protégés ou non vérifiables nécessitent une copie manuelle.',
 'docs/validation/corrector-compact.png'),
]

import ast
tree=ast.parse((ROOT/'Hub/fort_hub.py').read_text(encoding='utf-8'))
PRESETS=next(ast.literal_eval(node.value) for node in tree.body if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PRESETS' for t in node.targets))
def copy_capture(source,stem):
    src=ROOT/source;dest=OUT/'captures'/f'{stem}.png'
    if src.name=='applinator-polished-widget.png':
        # Keep the actual widget, omitting the empty full-screen backdrop.
        with PILImage.open(src) as im:im.crop((601,358,1320,723)).save(dest)
    else:shutil.copy2(src,dest)
    return dest

hub=copy_capture('docs/validation/ergonatus-updated-compiled.png','01-hub')
launcher=copy_capture('docs/validation/ergonatus-launcher-opacity.png','02-lanceur-opacite')
orb=copy_capture('assets/orbs/ergonatus-orb.png','03-orb-ergonatus')
for i,app in enumerate(APPS):copy_capture(app[5],f'{i+4:02d}-{app[0].lower().replace("é","e")}')
EXTRAS=[('calculinator-fraction-polished.png','22-fractions'),('planinator-widget.png','23-agenda-widget'),('planinator-subject-picker.png','24-matieres'),('temporator-polished-numbers.png','25-timer-chiffres'),('organisator-spaces.png','26-mes-espaces'),('applinator-choice-settings.png','27-choix-applications')]
for file,stem in EXTRAS:copy_capture('docs/validation/'+file,stem)

INTRO='Ergonatus rassemble 18 applications Windows autour d’un hub unique. La suite aide à écrire, lire, communiquer, calculer, organiser ses documents et gérer son quotidien. Les Orbs flottantes donnent accès aux outils sans encombrer l’écran de fenêtres permanentes.'
GUIDE=[
 'Lancer Ergonatus : les logiciels cochés du profil actif démarrent automatiquement. Les instances déjà ouvertes sont reconnues.',
 'Choisir un profil prépare une sélection adaptée ; Charger le profil lance les logiciels cochés. Les choix modifiés sont mémorisés.',
 'Cliquer sur l’Orb Ergonatus ouvre le panneau des 18 raccourcis ; cliquer sur une tuile ouvre son logiciel. Le fond ou Échap masque le panneau.',
 'Le curseur Fond règle l’opacité du panneau de 10 à 100 %, sans rendre les tuiles transparentes. Le réglage est conservé.',
 'Double-cliquer sur l’Orb ou choisir Ouvrir Ergonatus dans son menu affiche le hub. Glisser la barre du haut déplace la fenêtre.',
 'Les boutons ? expliquent chaque logiciel. Les interrupteurs choisissent les applications ; Avec Windows ajoute un démarrage à l’ouverture de session.',
 'L’Orb Ergonatus est placée en bas à droite, au-dessus de la barre des tâches. Les autres Orbs s’empilent au-dessus, avec un espacement régulier.',
 'Seul Ergonatus affiche une icône dans la zone de notification. Masquer le hub garde les aides ouvertes ; Quitter Ergonatus demande la fermeture de toute la suite.',
]
FAMILIES=[('Écriture et voix','Claviernator, Transcrinator, Redactor, Écrinator, Corrector, Lector, Scanator, Traductor.'),('Apprentissage et communication','Calculinator, PDFinator, Communicator, Planinator.'),('Confort et organisation','Precisionator, Concentrator, Temporator, Memorinator, Organisator, Applinator.')]
LIMITS=[
 'Cette archive est une présentation : elle contient des documents et des captures, pas les exécutables, modèles ni préférences personnelles.',
 'Les fonctions de texte, traduction et voix décrites comme locales utilisent les moteurs et ressources livrés avec la suite. Garder le dossier Ergonatus complet ; les temps de chargement dépendent du PC.',
 'Les textes générés, reconnus ou corrigés restent à relire. La qualité de la reconnaissance dépend des documents, de l’audio et des langues disponibles.',
 'Les données des applications sont enregistrées localement. Les préférences principales sont sous %LOCALAPPDATA%/Ergonatus ; les espaces Organisator et leurs fichiers restent à leur emplacement choisi.',
 'Les captures sont des illustrations de validation et de démonstration déjà produites pendant le développement. Les quatre outils historiques sont illustrés par leurs captures de référence ; quelques libellés peuvent différer de la version actuelle.',
 'Le résumé décrit l’état de la suite au 19 octobre 2026. Gestinator et Copinator ont été retirés ; Dictator a été remplacé par Applinator.',
]

# PDF: fixed page composition makes screenshots and page breaks predictable.
for name,file in [('Segoe','segoeui.ttf'),('SegoeBold','segoeuib.ttf')]:pdfmetrics.registerFont(TTFont(name,str(Path('C:/Windows/Fonts')/file)))
PDF=OUT/'Ergonatus_Presentation_complete.pdf';c=canvas.Canvas(str(PDF),pagesize=(595.276,841.89));c.setTitle('Ergonatus - Présentation complète');c.setAuthor('Ergonatus')
W,H=595.276,841.89;PAGE=0;layout=[]
def para(text,x,y,width=499,size=10.8,color='#25374B',bold=False):
    p=Paragraph(html.escape(text),ParagraphStyle('p',fontName='SegoeBold' if bold else 'Segoe',fontSize=size,leading=size*1.42,textColor=HexColor(color)))
    _,height=p.wrap(width,1000);p.drawOn(c,x,y-height);return y-height-9
def start(title,kicker='PRÉSENTATION DE LA SUITE'):
    global PAGE
    PAGE+=1;c.setFillColor(HexColor('#F5F8FC'));c.rect(0,0,W,H,fill=1,stroke=0)
    c.setFillColor(HexColor('#152840'));c.rect(0,H-143,W,143,fill=1,stroke=0)
    para(kicker,48,H-33,size=8.2,color='#80C1CF',bold=True)
    para(title,48,H-66,size=25,color='#FFFFFF',bold=True)
    c.setFillColor(HexColor('#688098'));c.setFont('Segoe',8);c.drawString(48,28,'ERGONATUS  /  19 OCTOBRE 2026');c.drawRightString(W-48,28,f'{PAGE:02d}')
    return H-170
def figure(path,top,bottom=73,caption='Capture de démonstration'):
    with PILImage.open(path) as im:iw,ih=im.size
    maxw=499;maxh=top-bottom-24;scale=min(maxw/iw,maxh/ih);w,h=iw*scale,ih*scale
    x=(W-w)/2;y=top-h;c.setFillColor(HexColor('#E1E8F0'));c.roundRect(x-5,y-5,w+10,h+10,8,fill=1,stroke=0)
    c.drawImage(ImageReader(str(path)),x,y,w,h,mask='auto');para(caption,48,y-14,size=8.3,color='#62748A')
    assert y>=bottom+20,(path,y)
def finish():c.showPage()
y=start('Vos outils. À portée d’Orb.','ERGONATUS  /  GUIDE ILLUSTRÉ')
y=para(INTRO,48,y,size=13)
y=para('Un hub, 18 applications, des profils adaptés et des widgets discrets.',48,y-7,size=12,bold=True)
figure(launcher,y-22,caption='Le lanceur de la suite : tous les logiciels et le réglage d’opacité du fond.');finish()
y=start('Le hub au quotidien')
for text in GUIDE[:2]:y=para(text,48,y)
figure(hub,y-12,caption='Fenêtre du hub : profil, sélection, démarrage Windows et aide par logiciel.');finish()
y=start('Les Orbs et les commandes')
for text in GUIDE[2:]:y=para(text,48,y)
y=para('Repère : chaque logiciel possède son propre geste d’Orb. Les fiches suivantes précisent les cas particuliers.',48,y-10,bold=True)
c.drawImage(ImageReader(str(orb)),W/2-44,95,88,88,mask='auto');finish()
y=start('Un profil pour commencer')
y=para('Les profils sont des points de départ modifiables, pas une prescription. Personnalisé permet de choisir librement les outils. Changer de profil prépare la sélection ; Charger le profil l’active.',48,y)
for name,keys in PRESETS.items():
    y=para(name,48,y-5,size=11,bold=True)
    names=[next((a[0] for a in APPS if a[0].lower().replace('é','e')==k),k.title()) for k in keys]
    y=para(', '.join(names)+'.',48,y,size=10)
assert y>55;finish()
y=start('La suite en un regard')
for title,text in FAMILIES:y=para(title,48,y-15,size=15,bold=True);y=para(text,48,y,size=12)
y=para('Parcours de lecture',48,y-15,size=15,bold=True)
y=para('Une fiche par application suit ce panorama, puis trois exemples d’usage et les informations pratiques. Les captures sont également disponibles en PNG dans le dossier captures.',48,y,size=12)
y=para('Dans ce ZIP : PDF illustré, présentation HTML hors ligne, résumé texte et 27 captures.',48,y-10,bold=True);finish()
for i,(name,role,features,usage,boundary,source) in enumerate(APPS):
    y=start(name,role.upper())
    for text in features:y=para('• '+text,48,y,size=10.2)
    y=para('Pour commencer : '+usage,48,y-2,size=10.2,bold=True)
    y=para('À savoir : '+boundary,48,y,size=9.4,color='#62748A')
    image=OUT/'captures'/f'{i+4:02d}-{name.lower().replace("é","e")}.png'
    figure(image,y-8,caption=('Capture de référence de l’application.' if i<4 else 'Capture de validation ou de démonstration.'));finish()
y=start('Trois parcours très simples')
for title,text in [
 ('Un élève prépare ses devoirs','Planinator indique les matières et les tâches. Scanator récupère un énoncé, Lector le lit, Calculinator aide à calculer, puis Corrector relit la réponse. Temporator peut rythmer la séance.'),
 ('Une personne préfère dicter','Transcrinator produit le premier texte. Redactor aide à le reformuler, Corrector propose une correction, puis Lector permet de le réécouter. Applinator ouvre rapidement le logiciel dans lequel le texte sera utilisé.'),
 ('Une journée mieux organisée','Planinator affiche aujourd’hui et demain. Memorinator garde les idées à portée de main. Applinator ouvre les applications favorites et Organisator propose de ranger les documents dans l’espace adapté.')]:
    y=para(title,48,y-14,size=15,bold=True);y=para(text,48,y,size=12)
y=para('Chacun peut ne garder que quelques outils. L’intérêt du hub est de retrouver la bonne sélection dès son lancement.',48,y-16,size=12,bold=True);finish()
y=start('Données, périmètre et repères')
for text in LIMITS:y=para('• '+text,48,y,size=10.8)
y=para('Repères de validation récents',48,y-8,size=13,bold=True)
y=para('Hub : 46 tests lors de la mise à jour des Orbs et de la fermeture groupée ; 11 tests ciblés pour l’opacité ; 14 pour le démarrage sélectionné. Le démarrage automatique d’Écrinator a aussi été observé dans le programme compilé avec un profil de test isolé. Ces vérifications ne constituent pas un audit exhaustif des 18 applications.',48,y,size=10.5)
assert y>55;finish();c.save()

# Offline HTML uses relative image paths and works without scripts or network access.
def esc(t):return html.escape(t)
def img(path,caption):return f'<figure><a href="captures/{path}"><img loading="lazy" src="captures/{path}" alt="{esc(caption)}"></a><figcaption>{esc(caption)}</figcaption></figure>'
nav=''.join(f'<a href="#app-{i}">{esc(a[0])}</a>' for i,a in enumerate(APPS))
parts=[f'<header><p class="eyebrow">GUIDE ILLUSTRÉ · 19 OCTOBRE 2026</p><h1>Ergonatus</h1><p class="lead">Vos outils. À portée d’Orb.</p><p>{esc(INTRO)}</p><div class="stats"><b>1 hub</b><b>18 applications</b><b>9 profils</b><b>27 captures</b></div></header>',
 '<section><h2>Le hub et ses Orbs</h2><ol>'+''.join('<li>'+esc(t)+'</li>' for t in GUIDE)+'</ol>'+img('01-hub.png','Hub actuel - sélection des logiciels')+img('02-lanceur-opacite.png','Panneau de raccourcis - curseur d’opacité du fond')+'</section>',
 '<section><h2>Les profils</h2><p>Personnalisé : vos propres choix. Les huit autres profils préparent les sélections suivantes, toujours modifiables.</p><div class="profiles">'+''.join('<article><h3>'+esc(n)+'</h3><p>'+esc(', '.join(k.title() for k in keys))+'</p></article>' for n,keys in PRESETS.items())+'</div></section>',
 '<section><h2>Les 18 logiciels</h2><nav>'+nav+'</nav></section>']
for i,(name,role,features,usage,boundary,source) in enumerate(APPS):
    filename=f'{i+4:02d}-{name.lower().replace("é","e")}.png'
    parts.append(f'<section id="app-{i}"><p class="eyebrow">{i+1:02d} / 18</p><h2>{esc(name)}</h2><p class="lead">{esc(role)}</p><ul>'+''.join('<li>'+esc(t)+'</li>' for t in features)+f'</ul><p><strong>Pour commencer.</strong> {esc(usage)}</p><p class="note"><strong>À savoir.</strong> {esc(boundary)}</p>'+img(filename,'Capture de référence' if i<4 else 'Capture de validation ou de démonstration')+'</section>')
parts.append('<section><h2>Autres vues</h2>'+''.join(img(stem+'.png',stem[3:].replace('-',' ').capitalize()) for _,stem in EXTRAS)+'</section>')
parts.append('<section><h2>Informations pratiques</h2><ul>'+''.join('<li>'+esc(t)+'</li>' for t in LIMITS)+'</ul></section>')
css='''*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#0c1423;color:#dce7f6;font:17px/1.65 "Segoe UI",Arial,sans-serif}main{max-width:1100px;margin:auto;padding:48px 28px}header{padding:50px 0}h1{font-size:76px;line-height:1.05;letter-spacing:-3px;margin:12px 0}h2{font-size:34px;color:white;margin:10px 0}h3{margin:0;color:#93d1df}.eyebrow{letter-spacing:3px;font-size:12px;color:#8ac3d2}.lead{font-size:24px;color:#b6d9e5}.stats,nav{display:flex;flex-wrap:wrap;gap:12px}.stats b,nav a{padding:10px 16px;background:#213850;border-radius:10px}a{color:#bde3ee;text-decoration:none}section{padding:36px;margin:30px 0;background:#142238;border:1px solid #2d4562;border-radius:24px;scroll-margin:20px}li{margin:12px 0}figure{margin:26px 0}img{max-width:100%;max-height:720px;display:block;margin:auto;border-radius:12px;object-fit:contain}figcaption{font-size:13px;color:#91a8c0;margin-top:10px;text-align:center}.note{border-left:3px solid #589caf;padding:12px 20px;background:#182c42}.profiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px}.profiles article{padding:20px;background:#1a3047;border-radius:12px}@media(max-width:600px){main{padding:15px}section{padding:20px}h1{font-size:52px}h2{font-size:28px}}@media print{body{background:white;color:#172638}section{break-inside:avoid;background:white;border-color:#ccd5df}h2{color:#172638}nav{display:none}}'''
(OUT/'Ouvrir_la_presentation.html').write_text('<!doctype html><html lang="fr"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Ergonatus - Guide illustré</title><style>'+css+'</style><main>'+''.join(parts)+'</main></html>',encoding='utf-8')
text=['ERGONATUS - PRÉSENTATION COMPLÈTE','État au 19 octobre 2026','',INTRO,'','LE HUB ET LES ORBS',*GUIDE,'','PROFILS','Personnalisé : sélection libre.']
text += [n+' : '+', '.join(keys) for n,keys in PRESETS.items()]
for name,role,features,usage,boundary,_ in APPS:text += ['',name.upper()+' - '+role,*['- '+t for t in features],'Pour commencer : '+usage,'À savoir : '+boundary]
text+=['','INFORMATIONS PRATIQUES',*LIMITS]
(OUT/'Resume_complet.txt').write_text('\n'.join(text),encoding='utf-8')
(OUT/'LISEZ-MOI.txt').write_text('ERGONATUS - GUIDE ILLUSTRÉ\n\n1. Extraire entièrement le ZIP.\n2. Ouvrir Ergonatus_Presentation_complete.pdf pour le document illustré.\n3. Ou ouvrir Ouvrir_la_presentation.html pour la version hors ligne avec images agrandissables.\n\nLe dossier captures contient les 27 PNG. Resume_complet.txt fournit le texte seul.\nCette archive ne contient aucun logiciel, modèle ou profil utilisateur.\nCaptures : démonstrations et références de validation, pas une session personnelle exportée.\n',encoding='utf-8')
manifest=[]
for p in sorted((OUT/'captures').glob('*.png')):
    with PILImage.open(p) as im:w,h=im.size
    manifest.append({'file':'captures/'+p.name,'width':w,'height':h,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(OUT/'Inventaire_captures.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
reader=PdfReader(PDF);assert len(reader.pages)==25,len(reader.pages)
assert len(manifest)==27,len(manifest)
for a in APPS:assert any(a[0] in (p.extract_text() or '') for p in reader.pages),a[0]
sheet=PILImage.new('RGB',(1000,((len(manifest)+3)//4)*200),'#edf2f8');draw=ImageDraw.Draw(sheet)
for i,m in enumerate(manifest):
    with PILImage.open(OUT/m['file']) as im:
        im=im.convert('RGBA');thumb=PILImage.new('RGBA',im.size,'#142238');thumb.alpha_composite(im);thumb=thumb.convert('RGB');thumb.thumbnail((230,168))
        x=(i%4)*250;y=(i//4)*200;sheet.paste(thumb,(x+(250-thumb.width)//2,y));draw.text((x+8,y+174),Path(m['file']).stem,fill='#142238')
sheet.save(TMP/'captures-contact.png')
print(json.dumps({'pdf_pages':len(reader.pages),'captures':len(manifest),'folder':str(OUT)},ensure_ascii=False))
