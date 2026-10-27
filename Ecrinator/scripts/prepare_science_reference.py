"""Curate a finite, named list of college-useful scientific SVG illustrations.
No bulk category import. One greyscale rendering per original, no colour variants.
"""
from pathlib import Path
from zipfile import ZipFile
from io import BytesIO
import json,re,hashlib
from urllib.parse import quote
from xml.etree import ElementTree as E
from PIL import Image,ImageColor,ImageDraw,ImageFont,ImageChops
import cairosvg
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'test-output/reference-sources';OUT=ROOT/'assets/library/reference/science';OUT.mkdir(parents=True,exist_ok=True)
GROUPS=[
('Human_physiology','Le corps humain et la santé',['5e','4e','3e'],'Repérer les organes et légender le schéma sans confondre organe et fonction.',{
'healthy_liver':'Foie sain','aorta':'Aorte','bladder':'Vessie','brain-1':'Cerveau · vue externe','breathing-expiration':'Expiration','breathing-inspiration':'Inspiration','capillaries':'Réseau de capillaires sanguins','colon':'Gros intestin','digestive-system':'Appareil digestif','ear':'Oreille','eye-crosssection':'Œil · coupe','eye-normal-vision':'Vision normale','gas-exchange-pulmonary':'Échanges gazeux dans les poumons','healthy-bronchus-crosssection':'Bronche saine · coupe','healthy-lung':'Poumon sain','heart-chambers-visible':'Cœur · cavités visibles','heart-front':'Cœur · vue de face','heart-outline':'Cœur · contour à compléter','heart-valves':'Valvules du cœur','intestinal-villi':'Villosités intestinales','kidney-1':'Rein','lung':'Poumons','muscle-tendon':'Muscle et tendon','musculature-front':'Muscles · vue de face','musculature-back':'Muscles · vue de dos','nasal-cavity':'Fosses nasales','oral-cavity':'Cavité buccale','pancreas':'Pancréas','pulmonary-circulation':'Circulation pulmonaire','salivary-glands':'Glandes salivaires','skin-normal':'Peau · coupe','small-intestine':'Intestin grêle','stomach':'Estomac','teeth-adult':'Dentition adulte','teeth-child':'Dentition de l’enfant','tongue':'Langue','tooth':'Dent · coupe','trachea-bronchi':'Trachée et bronches','vein-crosssection':'Veine · coupe','vascular-tunic-artery':'Artère · paroi','Motor_neuron':'Neurone moteur','Sensory_neuron':'Neurone sensitif','Arteries_and_veins':'Artères et veines','view_of_thoracic_skelton':'Squelette du thorax'}),
('Plants_Algae','Le vivant, sa diversité et ses fonctions',['6e','5e','4e','3e'],'Observer les structures végétales et comparer des êtres vivants.',{
'DicotSeedling':'Plantule · dicotylédone','Leaf':'Feuille','Lemna':'Lentille d’eau','MossColony':'Mousse · colonie','Moss_Gametophore':'Mousse · tige feuillée','TomatoFruit':'Tomate · fruit','carrot':'Carotte','potato':'Pomme de terre · tubercule','white-beans':'Graines de haricot','Fern_palm':'Fougère','Ginkgo':'Ginkgo','Rice':'Riz','wheat':'Blé','Oat':'Avoine','Rye':'Seigle','Zea_mays_cartoon':'Maïs · plante','Arabidopsis_Flower':'Fleur · organisation','Arabidopsis_root_cross_section':'Racine · coupe transversale','Arabidopsis_root_longitudinal_section':'Racine · coupe longitudinale','Arabidopsis_one_plant_in_soil':'Plante et racines dans le sol','plant-axes':'Organisation d’une plante','volvox':'Volvox · colonie d’algues'}),
('Animals','Biodiversité et classification',['6e','5e','4e','3e'],'Comparer les caractères visibles pour construire une classification des êtres vivants.',{
'cat':'Chat','dog':'Chien','horse':'Cheval','ox':'Bovin','sheep':'Mouton','snail':'Escargot','Ant':'Fourmi','Beetle':'Coléoptère','Common_carp':'Carpe','Common_house_spider':'Araignée','Culex_pipiens_mosquito':'Moustique commun','European_honey_bee_adult':'Abeille · adulte','European_honey_bee_illustration':'Abeille · organisation','Japanese_earthworm':'Lombric','Moon_jellyfish':'Méduse','Pill_bug':'Cloporte','Silkworm':'Ver à soie · chenille','Swallowtail':'Papillon · machaon','Chambered_nautilus':'Nautile','East_asian_common_octopus':'Poulpe','African_clawed_frog':'Grenouille · xénope','crow':'Corneille','earwig':'Perce-oreille','fish_skeleton':'Squelette d’un poisson','ladybird_bug_beetle':'Coccinelle','walking_stick':'Phasme','wasp':'Guêpe','shark':'Requin','honey_bee_hive':'Ruche','honey_bee_eggs':'Abeille · œufs','honey_bee_larva':'Abeille · larve','honey_bee_pupa':'Abeille · nymphe','honey_take_bee_pollen':'Abeille et pollen','silk_moth_cocoon':'Ver à soie · cocon','fish_eggs':'Œufs de poisson'}),
('Intracellular_components','Organisation cellulaire',['6e','5e','4e','3e'],'Repérer les constituants d’une cellule et relier structure et fonctionnement.',{
'Average_prokaryote_cell-_unlabled':'Cellule bactérienne · sans légende','cell-complete':'Cellule · organisation interne','mitochondrium-1':'Mitochondrie','nucleus':'Noyau cellulaire','Endoplasmic_Reticulum':'Réticulum endoplasmique','golgi-2d-1':'Appareil de Golgi'}),
('Microbiology','Microorganismes et cellules',['6e','5e','4e','3e'],'Comparer les cellules et observer la diversité des microorganismes.',{
'Yeast':'Levure','generic-bacterium':'Bactérie · forme générale','bacterium-interior':'Bactérie · organisation interne','bacterium':'Bactérie','Bacillus_subtilis':'Bacille','fission_yeast':'Levure · division','Animal_cells':'Cellules animales','Plant_cells':'Cellules végétales','Fungal_cells':'Cellules de champignon','Egg_cell':'Cellule reproductrice · ovule','Spermatozoa_cell':'Cellule reproductrice · spermatozoïde','Neuron_cells':'Cellules nerveuses','Muscle_cells':'Cellules musculaires','Epithelial_cells':'Cellules épithéliales'}),
('Chemistry','Matériel et démarche expérimentale',['6e','5e','4e','3e'],'Reconnaître le matériel et préparer un schéma de montage expérimental.',{
'beaker-empty':'Bécher vide','Beaker_water':'Bécher avec eau','erlenmeyer-glass':'Erlenmeyer','funnel-glass':'Entonnoir','funnel-paper':'Papier filtre dans un entonnoir','filtration-1':'Filtration · montage','filtration-2':'Filtration · autre montage','measuringcylinder-empty':'Éprouvette graduée vide','measuring-jug':'Récipient gradué','pipette-glass':'Pipette en verre','testtube-glass':'Tube à essai','separating-funnel':'Ampoule à décanter','mortar':'Mortier et pilon','u-tube':'Tube en U','Reagent_bottle':'Flacon de réactif','graded-measuring-cylinder':'Éprouvette graduée'}),
('Lab_apparatus','Observer et expérimenter',['6e','5e','4e','3e'],'Identifier les instruments, construire un protocole et légender un montage.',{
'microscope':'Microscope optique','microscope-cartoon':'Microscope · dessin simplifié','distillation':'Distillation · montage','glass-rod':'Agitateur en verre','laboratory-stands':'Support de laboratoire','scale':'Balance','magnet':'Aimant','paper-chromatography':'Chromatographie sur papier','paper-chromatography-run':'Chromatographie · séparation','glassslideflat':'Lame de microscope','labcoat':'Blouse de laboratoire','ph-meter':'pH-mètre','tube-rack':'Portoir de tubes','three-neck-flask':'Ballon à trois cols','lab-tong':'Pince de laboratoire'}),
('Computer_hardware','Objets et systèmes techniques',['5e','4e','3e'],'Identifier les constituants matériels d’un système informatique.',{
'cpu':'Processeur','hdd':'Disque dur','laptop':'Ordinateur portable','screen':'Écran','Server_rack':'Baie de serveurs'})]
licenses={'cc-0':('CC0 1.0','https://creativecommons.org/publicdomain/zero/1.0/'),'cc-by-3.0':('CC BY 3.0','https://creativecommons.org/licenses/by/3.0/'),'cc-by-4.0':('CC BY 4.0','https://creativecommons.org/licenses/by/4.0/'),'cc-by-sa-3.0':('CC BY-SA 3.0','https://creativecommons.org/licenses/by-sa/3.0/'),'cc-by-sa-4.0':('CC BY-SA 4.0','https://creativecommons.org/licenses/by-sa/4.0/')}
z=ZipFile(BASE/'bioicons-source.zip');commit=z.comment.decode();assert re.fullmatch('[0-9a-f]{40}',commit)
metadata=json.loads((BASE/'bioicons-icons.json').read_text(encoding='utf-8'));names=z.namelist();entries=[];excluded=[];seen=set()
def grey(value):
 try:
  rgb=ImageColor.getrgb(value);v=round(.299*rgb[0]+.587*rgb[1]+.114*rgb[2]);return '#%02x%02x%02x'%(v,v,v)
 except(ValueError,TypeError):return value
style_re=re.compile(r'((?:fill|stroke|stop-color|color)\s*:\s*)([^;}]+)')
def deny(url,resource_type):raise ValueError('External SVG reference is not allowed: '+str(url))
VISUAL_EXCLUSIONS={
 'Fern_palm':'Silhouette ambiguë de type palmier ; ne pas étiqueter fougère.',
 'European_honey_bee_adult':'Dessin avec dispositif attaché, inadapté à une planche de classification simple.',
 'European_honey_bee_illustration':'Abeilles anthropomorphisées ; pas un schéma anatomique.',
 'Endoplasmic_Reticulum':'Détail cellulaire trop avancé pour ce lot collège.',
 'golgi-2d-1':'Détail cellulaire trop avancé pour ce lot collège.',
 'filtration-1':'Filtration spécialisée, ne représente pas le montage scolaire gravitaire.',
 'filtration-2':'Filtration sur membrane spécialisée, hors objectif du lot collège.',
 'fish_skeleton':'Fond noir et dessin stylisé, peu adapté à un schéma à compléter.'
}
for category,topic,grades,objective,selection in GROUPS:
 for name,title in selection.items():
  if name in VISUAL_EXCLUSIONS:excluded.append(dict(name=name,reason=VISUAL_EXCLUSIONS[name]));continue
  candidates=[e for e in metadata if e['category']==category and e['name']==name and e['license']in licenses]
  if not candidates:excluded.append(dict(name=name,reason='No record with an allowed licence'));continue
  record=candidates[0];suffix='/'+category+'/'+record['author']+'/'+name+'.svg';paths=[p for p in names if p.endswith(suffix) and '/'+record['license']+'/'in p]
  if len(paths)!=1:excluded.append(dict(name=name,reason='Ambiguous source path'));continue
  source=paths[0];raw=z.read(source);tree=E.fromstring(raw)
  printed=' '.join(t for e in tree.iter()if e.tag.rsplit('}',1)[-1]in ['text','tspan']for t in e.itertext()).strip()
  if printed:excluded.append(dict(name=name,reason='Printed labels require separate review',text=printed[:150]));continue
  for element in tree.iter():
   for key,value in list(element.attrib.items()):
    if key in ['fill','stroke','stop-color','color']:element.set(key,grey(value))
    elif key=='style':element.set(key,style_re.sub(lambda m:m[1]+grey(m[2].strip()),value))
   if element.tag.rsplit('}',1)[-1]=='style'and element.text:element.text=style_re.sub(lambda m:m[1]+grey(m[2].strip()),element.text)
  converted=E.tostring(tree,encoding='utf-8');ident='bio-'+hashlib.sha256(source.encode()).hexdigest()[:16];file=OUT/(ident+'.png')
  try:
   box=[float(n) for n in re.split(r'[ ,]+',tree.get('viewBox','').strip()) if n]
   if len(box)!=4:
    width=float(re.match(r'[0-9.]+',tree.get('width','1000'))[0]);height=float(re.match(r'[0-9.]+',tree.get('height','1000'))[0]);box=[0.,0.,width,height]
   def render(root,box):
    root.set('viewBox',' '.join(str(v)for v in box));root.set('width',str(box[2]));root.set('height',str(box[3]));factor=min(1100/box[2],1100/box[3]);
    raw=E.tostring(root,encoding='utf-8')
    image=cairosvg.surface.PNGSurface.convert(bytestring=raw,url_fetcher=deny,output_width=max(1,round(box[2]*factor)),output_height=max(1,round(box[3]*factor)))
    return Image.open(BytesIO(image)).convert('RGBA'),raw
   im,converted=render(tree,box)
   white=Image.new('RGBA',im.size,'white');white.alpha_composite(im)
   mask=ImageChops.difference(white.convert('RGB'),Image.new('RGB',im.size,'white')).convert('L').point(lambda p:255 if p>3 else 0)
   bbox=mask.getbbox()
   if bbox is None:raise ValueError('Blank drawing')
   # Tighten the vector viewport, preserving complete paths with a 4% safety margin.
   l,t,r,b=bbox;pad=max(4,round(max(r-l,b-t)*.04));l=max(0,l-pad);t=max(0,t-pad);r=min(im.width,r+pad);b=min(im.height,b+pad)
   newbox=[box[0]+l/im.width*box[2],box[1]+t/im.height*box[3],(r-l)/im.width*box[2],(b-t)/im.height*box[3]]
   im,converted=render(tree,newbox)
   bg=Image.new('RGBA',im.size,'white');bg.alpha_composite(im);im=bg.convert('RGB');im.save(file,optimize=True)
   sha=hashlib.sha256(file.read_bytes()).hexdigest()
   if sha in seen:excluded.append(dict(name=name,reason='Duplicate rendered figure'));continue
   seen.add(sha);small=im.copy();small.thumbnail((280,170));small.save(OUT/(ident+'-thumb.png'),optimize=True)
   (OUT/(ident+'-original.svg')).write_bytes(raw);(OUT/(ident+'-gris.svg')).write_bytes(converted)
   license,license_url=licenses[record['license']];relative=source.split('/',1)[1]
   subject='Technologie'if category=='Computer_hardware'else 'Physique-chimie'if category in ['Chemistry','Lab_apparatus']else'SVT'
   entries.append(dict(id=ident,title=title,category=subject,subjects=[subject],topic=topic,curriculum_theme=topic,learning_objective=objective,grades=grades,educational_use='À étudier'if category in ['Animals','Plants_Algae']else'À compléter',kind='Illustration du vivant'if category in ['Animals','Plants_Algae']else'Schéma à légender'if subject=='SVT'else'Illustration de matériel',language='zxx',source_name=name,monochrome=all(max(pixel)-min(pixel)<3 for pixel in small.getdata()),unlabelled=True,filename=file.name,width=im.width,height=im.height,sha256=sha,author=record['author'],license=license,license_url=license_url,source_url='https://github.com/duerrsimon/bioicons/blob/'+commit+'/'+quote(relative,safe='/'),source_timestamp=commit,license_proof_url='https://github.com/duerrsimon/bioicons/blob/'+commit+'/static/icons/icons.json',changes='Palette vectorielle en niveaux de gris et viewport resserré autour du dessin ; tracés conservés ; PNG optimisé. Une seule version comptée.',source_svg=ident+'-original.svg',processed_svg=ident+'-gris.svg',review_status='À vérifier visuellement'))
  except Exception as error:excluded.append(dict(name=name,reason=str(error)))
(OUT/'candidates.json').write_text(json.dumps(entries,ensure_ascii=False,indent=2),encoding='utf-8');(OUT/'exclusions.json').write_text(json.dumps(excluded,ensure_ascii=False,indent=2),encoding='utf-8')
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',13)
for start in range(0,len(entries),24):
 sheet=Image.new('RGB',(1200,1200),'#edf2f8');draw=ImageDraw.Draw(sheet)
 for j,e in enumerate(entries[start:start+24]):
  x=j%4*300;y=j//4*200;im=Image.open(OUT/(e['id']+'-thumb.png'));sheet.paste(im,(x+(300-im.width)//2,y+3));draw.text((x+8,y+176),e['title'][:42],font=font,fill='#172b4d');draw.text((x+8,y+191),e['id'],font=font,fill='#52627b')
 sheet.save(OUT/('review-'+str(start//24+1)+'.jpg'),quality=90)
print('Prepared',len(entries),'named scientific illustrations;',len(excluded),'excluded; not automatically published')
