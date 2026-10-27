"""Original compact SVG classroom diagrams; sources included under MIT.
These are simplified exercise supports, never photographic/anatomical references.
No network or generative model is required to rebuild these vector assets.
"""
from pathlib import Path
from io import BytesIO
from zipfile import ZipFile
import math,json,hashlib,html
from PIL import Image,ImageDraw,ImageFont
import cairosvg
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'assets/library'
catalog=json.loads((OUT/'catalog.json').read_text(encoding='utf-8'))
catalog=[e for e in catalog if not e['id'].startswith('college-fiche-')]
seen={e['sha256']for e in catalog};created=[]
def line(x1,y1,x2,y2,**kw):return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '+attrs(kw)+'/>'
def attrs(kw):return ' '.join(f'{k.replace("_","-")}="{v}"'for k,v in kw.items())
def path(d,**kw):return f'<path d="{d}" '+attrs(kw)+'/>'
def rect(x,y,w,h,**kw):return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" '+attrs(kw)+'/>'
def ellipse(x,y,rx,ry,**kw):return f'<ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{ry}" '+attrs(kw)+'/>'
def circle(x,y,r,**kw):return ellipse(x,y,r,r,**kw)
def poly(points,**kw):return f'<polygon points="'+ ' '.join(f'{x},{y}'for x,y in points)+'" '+attrs(kw)+'/>'
def arrow(x1,y1,x2,y2):return line(x1,y1,x2,y2,marker_end='url(#a)')
def grid(x,y,w,h,step=20):return ''.join(line(i,y,i,y+h,stroke_width='.6',stroke='#999')for i in range(x,x+w+1,step))+''.join(line(x,j,x+w,j,stroke_width='.6',stroke='#999')for j in range(y,y+h+1,step))
def leaders(points):return ''.join(path(f'M{x} {y} H{end} h30',stroke_dasharray='4 4',stroke_width='1')for x,y,end in points)
def add(slug,title,category,topic,body,kind='Schéma',subjects=None,desc=''):
 ident='college-fiche-'+slug
 svg=('<svg xmlns="http://www.w3.org/2000/svg" width="600" height="360" viewBox="0 0 600 360"><defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10" fill="black"/></marker></defs><g fill="none" stroke="#111" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">'+body+'</g></svg>').encode()
 png=cairosvg.svg2png(bytestring=svg,output_width=1050);im=Image.open(BytesIO(png)).convert('RGBA');base=Image.new('RGBA',im.size,'white');base.alpha_composite(im);im=base.convert('L').point(lambda v:0 if v<200 else 255,mode='1');buf=BytesIO();im.save(buf,format='PNG',optimize=True);data=buf.getvalue();sha=hashlib.sha256(data).hexdigest()
 if sha in seen:return
 seen.add(sha);name=ident+'.png';(OUT/name).write_bytes(data);small=im.copy();small.thumbnail((300,195));buf=BytesIO();small.save(buf,format='PNG',optimize=True);thumb=buf.getvalue();(OUT/'thumbs'/name).write_bytes(thumb);(OUT/'sources/light'/(ident+'.svg')).write_bytes(svg)
 entry=dict(id=ident,title=title,category=category,topic=topic,tags=f'{title} {topic} collège noir blanc sans légende à compléter {desc}',filename=name,author='Écrinator / Ergonatus',license='MIT',license_url='https://opensource.org/license/mit/',source_url='urn:ergonatus:ecrinator:illustration:'+slug,source_timestamp='25/10/2026',changes='Création vectorielle originale ; schéma scolaire simplifié, non à l’échelle ; source SVG incluse dans l’archive de ressources.',width=im.width,height=im.height,sha256=sha,thumbnail_sha256=hashlib.sha256(thumb).hexdigest(),source_sha256=hashlib.sha256(svg).hexdigest(),license_proof_url='https://opensource.org/license/mit/',embedded=True,level='college',kind=kind,monochrome=True,unlabelled=True,subjects=subjects or [category])
 catalog.append(entry);created.append(entry)
# Geometry: genuine distinct constructions and blank exercise supports.
shapes={'triangle-quelconque':[(140,290),(470,290),(235,60)],'triangle-rectangle':[(150,290),(470,290),(150,60)],'triangle-isocele':[(140,290),(460,290),(300,55)],'triangle-equilateral':[(150,290),(450,290),(300,30.192)],'triangle-obtus':[(100,290),(500,290),(195,205)],'carre':[(180,60),(420,60),(420,300),(180,300)],'rectangle':[(120,90),(480,90),(480,270),(120,270)],'losange':[(300,40),(500,180),(300,320),(100,180)],'parallelogramme':[(160,90),(490,90),(420,270),(90,270)],'trapeze':[(200,80),(400,80),(510,285),(90,285)],'pentagone':[(300+145*math.cos(-math.pi/2+i*2*math.pi/5),180+145*math.sin(-math.pi/2+i*2*math.pi/5))for i in range(5)],'hexagone':[(300+145*math.cos(i*math.pi/3),180+145*math.sin(i*math.pi/3))for i in range(6)]}
for slug,points in shapes.items():add('geo-'+slug,slug.replace('-',' ').capitalize()+' — à annoter','Mathématiques','Géométrie plane',poly(points),kind='Figure géométrique')
for denominator in [2,3,4,5,6,8,10,12]:
 body=rect(70,95,460,170)+''.join(line(70+460*i/denominator,95,70+460*i/denominator,265)for i in range(1,denominator))
 add('fraction-bande-'+str(denominator),f'Bande fractionnée en {denominator} parts égales','Mathématiques','Fractions',body,kind='Support à compléter')
 body=circle(300,180,145)+''.join(line(300,180,300+145*math.cos(2*math.pi*i/denominator),180+145*math.sin(2*math.pi*i/denominator))for i in range(denominator))
 add('fraction-disque-'+str(denominator),f'Disque partagé en {denominator} parts égales','Mathématiques','Fractions',body,kind='Support à compléter')
for mode in ['positif','quatre-quadrants','orthonorme','points-a-placer']:
 body=grid(60,40,480,280,20)
 if mode=='positif':body+=arrow(60,320,555,320)+arrow(60,320,60,25)
 else:body+=arrow(45,180,555,180)+arrow(300,330,300,25)
 if mode=='points-a-placer':body+=''.join(circle(x,y,3,fill='black')for x,y in [(180,120),(380,100),(420,260),(240,240)])
 add('repere-'+mode,'Repère '+mode.replace('-',' ')+' — sans nombres','Mathématiques','Repérage et graphiques',body,kind='Support à compléter')
for n in [5,10,20]:
 body=arrow(60,180,550,180)+''.join(line(70+i*460/n,170,70+i*460/n,190)for i in range(n+1))
 add('droite-graduee-'+str(n),f'Droite graduée — {n} intervalles','Mathématiques','Repérage et graphiques',body,kind='Support à compléter')
for angle in [30,45,60,90,120,150]:
 a=math.radians(angle);body=line(170,290,500,290)+line(170,290,170+280*math.cos(a),290-280*math.sin(a))+path(f'M230 290 A60 60 0 0 0 {170+60*math.cos(a)} {290-60*math.sin(a)}')
 add('angle-'+str(angle),f'Angle de {angle}° — à mesurer ou compléter','Mathématiques','Angles',body,kind='Figure géométrique')
# Wireframe solids, plus real nets whose faces can be folded.
cube=poly([(170,105),(365,105),(365,300),(170,300)])+poly([(170,105),(250,45),(445,45),(365,105)])+poly([(365,105),(445,45),(445,240),(365,300)])+path('M170 300 L250 240 V45 M250 240 H445',stroke_dasharray='6 5')
add('cube','Cube — arêtes visibles et cachées','Mathématiques','Solides',cube,kind='Figure géométrique')
add('pave','Pavé droit — perspective','Mathématiques','Solides',f'<g transform="translate(-60 60) scale(1.25 .8)">{cube}</g>',kind='Figure géométrique')
add('cylindre','Cylindre — à annoter','Mathématiques','Solides',ellipse(300,80,115,38)+path('M185 80 V270 A115 38 0 0 0 415 270 V80')+path('M185 270 A115 38 0 0 1 415 270',stroke_dasharray='6 5'),kind='Figure géométrique')
add('cone','Cône — à annoter','Mathématiques','Solides',path('M175 285 L300 40 L425 285 A125 38 0 0 1 175 285')+path('M175 285 A125 38 0 0 1 425 285',stroke_dasharray='6 5'),kind='Figure géométrique')
add('sphere','Sphère — équateur et méridien','Mathématiques','Solides',circle(300,180,140)+ellipse(300,180,140,38)+ellipse(300,180,42,140),kind='Figure géométrique')
add('pyramide','Pyramide à base carrée','Mathématiques','Solides',poly([(130,265),(340,315),(470,235),(300,40)])+path('M300 40 L340 315 M130 265 L300 40 M130 265 L260 190 L470 235 M260 190 L300 40',stroke_dasharray='6 5'),kind='Figure géométrique')
for slug,cells in [('croix',[(1,0),(0,1),(1,1),(2,1),(1,2),(1,3)]),('bande',[(0,1),(1,1),(2,1),(3,1),(1,0),(2,2)])]:
 body=''.join(rect(100+x*75,25+y*75,75,75)for x,y in cells)
 add('patron-cube-'+slug,'Patron du cube — '+slug,'Mathématiques','Patrons de solides',body,kind='Support à compléter')
# Physics: European school circuit symbols, with actual closed wiring.
def lamp(x,y):return circle(x,y,20)+line(x-14,y-14,x+14,y+14)+line(x-14,y+14,x+14,y-14)
def battery(x,y):return line(x-6,y-24,x-6,y+24)+line(x+6,y-13,x+6,y+13)
def circuit(count=1,parallel=False,opened=False,resistor=False):
 b=path('M275 70 H110 V285 H490 V70 H287')+battery(281,70)
 if parallel:
  b=path('M275 55 H100 V300 H500 V55 H287')+battery(281,55)
  for y in [145,235]:b+=path(f'M100 {y} H280 M320 {y} H500')+lamp(300,y)
 else:
  b=path('M275 70 H110 V285 H490 V70 H287')+battery(281,70)
  if count==1:b+=rect(275,265,50,40,fill='white')if resistor else circle(300,285,22,fill='white')+lamp(300,285)
  else:
   for x in [220,380]:b+=circle(x,285,22,fill='white')+lamp(x,285)
 if opened:b+=rect(155,58,65,24,fill='white',stroke='none')+circle(160,70,3)+circle(215,70,3)+line(160,70,205,45)
 return b
for slug,title,kwargs in [('simple','Circuit fermé — pile et lampe',{}),('ouvert','Circuit ouvert — interrupteur',{'opened':True}),('serie','Deux lampes en série',{'count':2}),('derivation','Deux lampes en dérivation',{'parallel':True}),('serie-ouvert','Circuit série et interrupteur ouvert',{'count':2,'opened':True}),('resistance','Circuit — conducteur ohmique',{'resistor':True})]:add('circuit-'+slug,title,'Physique-chimie','Électricité',circuit(**kwargs))
for slug,body in [('pile',battery(300,180)+line(130,180,294,180)+line(306,180,470,180)),('lampe',lamp(300,180)+line(130,180,280,180)+line(320,180,470,180)),('resistance',rect(235,145,130,70)+line(100,180,235,180)+line(365,180,500,180)),('interrupteur',circle(230,180,5)+circle(380,180,5)+line(100,180,225,180)+line(385,180,500,180)+line(230,180,365,95)),('diode',poly([(255,130),(255,230),(345,180)])+line(345,125,345,235)+line(100,180,255,180)+line(345,180,500,180))]:add('symbole-'+slug,'Symbole normalisé — '+slug,'Physique-chimie','Symboles électriques',body)
for state in ['solide','liquide','gaz']:
 body=path('M160 65 V295 H440 V65')
 if state=='solide':pts=[(190+x*40,270-y*40)for x in range(6)for y in range(4)]
 elif state=='liquide':pts=[(185+x*40+(y%2)*13,275-y*34)for y in range(4)for x in range(6)]
 else:pts=[(190,100),(300,75),(390,135),(235,190),(350,235),(190,265),(410,280)]
 body+=''.join(circle(x,y,9)for x,y in pts)
 add('particules-'+state,'Modèle particulaire — '+state,'Physique-chimie','États de la matière',body)
for form in ['eau','dioxygene','dioxyde-carbone','dihydrogene','methane']:
 b={'eau':circle(300,180,48)+circle(238,235,27)+circle(362,235,27),'dioxygene':circle(255,180,48)+circle(345,180,48),'dioxyde-carbone':circle(215,180,45)+circle(300,180,38)+circle(385,180,45),'dihydrogene':circle(275,180,29)+circle(325,180,29),'methane':circle(300,180,42)+''.join(circle(x,y,24)for x,y in [(230,115),(370,115),(230,245),(370,245)])}[form]
 add('molecule-'+form,'Modèle moléculaire — '+form.replace('-',' '),'Physique-chimie','Molécules',b,desc='représentation plane simplifiée ; atomes non identifiés à compléter')
for slug,body in [('becher',path('M195 75 H425 L405 100 V295 H195 Z')+''.join(line(195,y,220,y)for y in range(130,280,30))),('eprouvette',rect(265,40,70,245)+rect(225,285,150,20)+''.join(line(265,y,285,y)for y in range(60,280,20))),('tube-essai',path('M250 40 V260 A50 50 0 0 0 350 260 V40 Z')),('erlenmeyer',path('M265 35 H335 V115 L440 295 H160 L265 115 Z')),('entonnoir',path('M140 55 H460 L320 205 V305 H280 V205 Z')),('thermometre',path('M285 60 A15 15 0 0 1 315 60 V245 A38 38 0 1 1 285 245 Z')+''.join(line(325,y,350,y)for y in range(70,235,25)))]:add('materiel-'+slug,slug.replace('-',' ').capitalize()+' — dessin de matériel','Physique-chimie','Matériel de laboratoire',body)
add('optique-reflexion','Réflexion — normale et rayon à compléter','Physique-chimie','Optique',line(80,250,520,250)+line(300,60,300,300,stroke_dasharray='6 5')+arrow(120,70,300,250))
add('optique-refraction','Réfraction — deux milieux à compléter','Physique-chimie','Optique',line(60,180,540,180)+line(300,35,300,325,stroke_dasharray='6 5')+arrow(140,40,300,180))
for k in [1,2,3]:
 pts=[(50+x,180+75*math.sin(x/500*2*math.pi*k))for x in range(501)]
 add('signal-'+str(k),f'Signal périodique — {k} période'+('s'if k>1 else''),'Physique-chimie','Signaux et ondes',arrow(40,180,560,180)+arrow(50,310,50,40)+path('M'+' L'.join(f'{x},{y}'for x,y in pts)))
# SVT simplified observation drawings, deliberately without printed labels.
animal=ellipse(280,180,190,120)+ellipse(270,180,48,39)+circle(280,180,10)+''.join(ellipse(x,y,23,11,transform=f'rotate({a} {x} {y})')+path(f'M{x-12} {y} l8 -5 l8 10 l8 -5',stroke_width='1')for x,y,a in [(160,155,-30),(360,110,20),(370,245,-20),(210,255,15)])
add('cellule-animale','Cellule animale — schéma simplifié sans légende','SVT','Cellules',animal+leaders([(285,165,510),(400,245,500),(440,150,510)]))
plant=rect(100,50,390,260,rx='28')+rect(112,62,366,236,rx='22')+rect(235,85,205,185,rx='32')+ellipse(175,180,39,31)+circle(180,180,8)+''.join(ellipse(x,y,19,9)for x,y in [(155,90),(180,260),(450,100),(450,250),(140,230)])
add('cellule-vegetale','Cellule végétale — schéma simplifié sans légende','SVT','Cellules',plant)
add('cellules-tissu','Tissu végétal — cellules à observer','SVT','Cellules',''.join(rect(100+x*100,55+y*80,100,80,rx='17')+ellipse(150+x*100,95+y*80,12,9)for y in range(3)for x in range(4)))
add('stomate','Stomate — schéma de deux cellules de garde','SVT','Végétaux',path('M275 55 C150 55 150 305 275 305 C225 210 225 150 275 55 Z M325 55 C450 55 450 305 325 305 C375 210 375 150 325 55 Z')+''.join(circle(x,y,9)for x,y in [(220,120),(210,180),(220,240),(380,120),(390,180),(380,240)]))
leaf=path('M300 300 C70 210 125 45 300 30 C475 45 530 210 300 300 Z M300 330 V45')+''.join(path(f'M300 {y} L{x} {y-60}')for x,y in [(200,240),(400,240),(190,185),(410,185),(235,125),(365,125)])
add('feuille','Feuille — nervures à légender','SVT','Végétaux',leaf)
add('plante-racines','Plante — racines, tige et feuilles','SVT','Végétaux',line(65,220,535,220,stroke_dasharray='5 5')+path('M300 280 V45 M300 95 C210 20 175 100 300 125 M300 155 C395 75 435 170 300 185 M300 250 L230 300 M300 260 L375 320 M300 275 L280 335 M265 275 L220 280 M350 298 L395 290'))
flower=''.join(ellipse(300+58*math.cos(i*math.pi/3),140+58*math.sin(i*math.pi/3),35,50,transform=f'rotate({i*60-90} {300+58*math.cos(i*math.pi/3)} {140+58*math.sin(i*math.pi/3)})')for i in range(6))+circle(300,140,32)+path('M300 240 V330')
add('fleur','Fleur vue de face — à légender','SVT','Végétaux',flower)
add('neurone','Neurone — organisation simplifiée','SVT','Système nerveux',path('M135 130 L165 110 L195 135 L205 180 L175 205 L135 180 Z M205 160 H440 M440 160 L500 115 M440 160 L510 160 M440 160 L500 205')+circle(166,158,16)+''.join(rect(x,148,40,24,rx='8')for x in [225,280,335,390])+path('M140 135 L95 90 L70 100 M100 100 L100 65 M135 170 L80 195 L60 235 M85 193 L55 180 M170 110 L175 55 L210 30 M175 70 L140 40'))
add('poumons','Appareil respiratoire — organisation simplifiée','SVT','Respiration',path('M285 30 V120 L245 165 M315 30 V120 L355 165 M275 110 C140 80 120 275 190 300 C235 310 275 265 275 160 M325 110 C460 80 480 275 410 300 C365 310 325 265 325 160')+path('M245 165 L210 205 M245 165 L225 250 M355 165 L390 205 M355 165 L375 250 M150 325 Q300 290 450 325'))
add('villosite','Villosité intestinale — forme à légender','SVT','Nutrition',path('M120 300 H180 V140 C180 20 360 20 360 140 V300 H450')+path('M220 300 V145 C220 80 320 80 320 145 V300',stroke_dasharray='5 5')+path('M270 300 V110'))
add('chromosome','Chromosome double — deux chromatides','SVT','ADN et reproduction',path('M190 50 C150 40 155 105 215 180 C155 255 150 320 190 310 C225 300 265 230 285 205 C310 230 350 300 385 310 C425 320 420 255 360 180 C420 105 425 40 385 50 C350 60 310 130 285 155 C265 130 225 60 190 50 Z')+circle(287,180,12))
add('volcan-coupe','Volcan — coupe simplifiée à légender','SVT','Géologie',path('M60 285 L225 140 L255 90 H340 L370 140 L540 285 Z M270 285 L280 120 H315 L330 285')+ellipse(300,305,75,27)+path('M285 200 L215 180 M310 230 L390 180 M70 280 L225 170 M90 280 L230 190 M370 170 L520 280',stroke_width='1.2'))
for move,arrows in [('divergence',arrow(240,100,130,100)+arrow(360,100,470,100)),('convergence',arrow(130,100,240,100)+arrow(470,100,360,100)),('coulissage',arrow(245,120,245,240)+arrow(355,240,355,120))]:add('plaques-'+move,'Plaques tectoniques — '+move,'SVT','Géologie',poly([(80,160),(280,160),(260,220),(80,220)])+poly([(320,160),(520,160),(520,220),(340,220)])+arrows)
for n in [3,4,5]:
 w=90;gap=(500-n*w)/(n-1);body=''
 for i in range(n):
  x=50+i*(w+gap);body+=rect(x,125,w,105,rx='9')
  if i<n-1:body+=arrow(x+w+4,177,x+w+gap-4,177)
 add('chaine-'+str(n),f'Chaîne alimentaire — {n} maillons à compléter','SVT','Écologie',body,kind='Support à compléter')
# Graphic/technology tools, blank timelines and actual blank music paper.
for n in [3,4,5,6]:
 body=arrow(50,190,550,190)
 for i in range(n):
  x=75+i*450/(n-1);body+=line(x,170,x,210)+rect(x-35,85 if i%2==0 else 225,70,65,rx='5')+line(x,150 if i%2==0 else 225,x,170 if i%2==0 else 210)
 add('frise-'+str(n),f'Frise chronologique — {n} événements à placer','Histoire-géographie','Frises à compléter',body,kind='Support à compléter',subjects=['Histoire-géographie','Français'])
for n in [3,4,5]:
 body=''.join(rect(75,30+i*58,450,48,rx='7')+ (arrow(300,80+i*58,300,88+i*58)if i<n-1 else'')for i in range(n))
 add('processus-'+str(n),f'Chaîne fonctionnelle — {n} étapes','Technologie','Analyse fonctionnelle',body,kind='Support à compléter')
add('algorithme-condition','Algorithme — condition oui / non à compléter','Technologie','Algorithmique',rect(240,25,120,40,rx='20')+arrow(300,65,300,95)+poly([(300,95),(380,150),(300,205),(220,150)])+arrow(220,150,115,150)+arrow(380,150,485,150)+rect(55,170,120,70,rx='6')+rect(425,170,120,70,rx='6')+path('M115 150 V170 M485 150 V170 M115 240 V290 H485 V240')+arrow(300,290,300,325),kind='Support à compléter')
add('chaine-information','Chaîne d’information — trois fonctions à compléter','Technologie','Analyse fonctionnelle',rect(45,125,130,90,rx='9')+rect(235,125,130,90,rx='9')+rect(425,125,130,90,rx='9')+arrow(175,170,235,170)+arrow(365,170,425,170),kind='Support à compléter')
for count in [1,2,3,4]:
 body=''.join(line(55,35+s*80+j*10,545,35+s*80+j*10,stroke_width='1.2')for s in range(count)for j in range(5))
 add('portees-'+str(count),f'Papier à musique — {count} portée'+('s'if count>1 else''),'Éducation musicale','Portées et rythme',body,kind='Support à compléter')
for beats in [2,3,4,6]:
 body=''.join(rect(70+b*460/beats,75+r*65,460/beats,65)for r in range(3)for b in range(beats))
 add('rythme-'+str(beats),f'Grille rythmique — {beats} pulsations par ligne','Éducation musicale','Portées et rythme',body,kind='Support à compléter')
body=''.join(rect(60+i*40,90,40,170)for i in range(12))+''.join(rect(60+i*40-10,90,20,100,fill='black')for i in [1,2,4,5,6,8,9,11])
add('clavier-piano','Clavier de piano — notes à placer','Éducation musicale','Instruments',body)
for n in [3,4,6]:
 cols=2 if n in [4,6]else 3;rows=math.ceil(n/cols);body=''.join(rect(40+(i%cols)*520/cols,30+(i//cols)*300/rows,500/cols,280/rows,rx='6')for i in range(n))
 add('bd-'+str(n),f'Planche de bande dessinée — {n} cases','Français','Raconter et organiser',body,kind='Support à compléter',subjects=['Français','Arts plastiques','Anglais','Espagnol','Allemand'])
for count in [3,4,5]:
 body=rect(225,135,150,80,rx='12')
 for i in range(count):
  a=2*math.pi*i/count;x=300+205*math.cos(a);y=175+115*math.sin(a);body+=line(300,175,x,y)+rect(x-65,y-28,130,56,rx='9',fill='white')
 add('carte-mentale-'+str(count),f'Carte mentale — {count} branches','Français','Raconter et organiser',body,kind='Support à compléter',subjects=['Français','EMC','SVT','Technologie','Histoire-géographie'])
for hour in [0,3,6,9]:
 body=circle(300,180,140)+''.join(line(300+125*math.sin(i*math.pi/6),180-125*math.cos(i*math.pi/6),300+138*math.sin(i*math.pi/6),180-138*math.cos(i*math.pi/6))for i in range(12))
 if hour:body+=line(300,180,300,65)+line(300,180,300+80*math.sin(hour*math.pi/6),180-80*math.cos(hour*math.pi/6))+circle(300,180,5,fill='black')
 add('horloge-'+str(hour),'Horloge sans chiffres — '+('aiguilles à dessiner'if hour==0 else str(hour)+' heures'),'Langues','Heures et quotidien',body,kind='Support à compléter',subjects=['Anglais','Espagnol','Allemand','Langues','Mathématiques'])
for vanishing in [1,2]:
 body=line(30,110,570,110,stroke_dasharray='6 5')
 points=[(300,110)]if vanishing==1 else[(35,110),(565,110)]
 for x,y in points:
  body+=circle(x,y,4,fill='black')+''.join(line(x,y,xx,320,stroke_width='1')for xx in [70,170,300,430,530])
 add('perspective-'+str(vanishing),f'Perspective — {vanishing} point'+('s'if vanishing>1 else'')+' de fuite','Arts plastiques','Perspective',body,kind='Support à compléter')
# Save catalog, original-source licence, and a real contact sheet for inspection.
(OUT/'catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'licenses/light/ecrinator-originals-MIT.txt').write_text((ROOT/'licenses/LICENSE-MIT').read_text(encoding='utf-8'),encoding='utf-8')
font=ImageFont.truetype(str(ROOT/'assets/fonts/NotoSerif-Variable.ttf'),12)
sample=created[::max(1,len(created)//30)][:30];sheet=Image.new('RGB',(1200,6*155),'#edf2f8');d=ImageDraw.Draw(sheet)
for i,e in enumerate(sample):
 x=(i%5)*240;y=(i//5)*155;im=Image.open(OUT/e['filename']).convert('RGB');im.thumbnail((220,125));sheet.paste(im,(x+10+(220-im.width)//2,y+5));d.text((x+10,y+132),e['title'][:31],font=font,fill='black')
sheet.save(ROOT/'test-output/college-originals-preview.jpg')
print(json.dumps(dict(created=len(created),total=len(catalog),image_bytes=sum((OUT/e['filename']).stat().st_size for e in created)),ensure_ascii=False))
