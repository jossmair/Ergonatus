from pathlib import Path
import json
rows='''France map Lambert-93 topographic-blank.svg|France · relief à compléter|France et ses territoires|3e|zxx|À compléter
France map Lambert-93 with rivers-blank.svg|France · fleuves à compléter|France et ses territoires|3e|zxx|À compléter
France map FR.png|France · grands repères géographiques|France et ses territoires|3e|fr|À étudier
France in the World.svg|La France dans le monde|France et ses territoires|3e|zxx|À compléter
France location map-Regions and departements-2016.svg|France · régions et départements (2016)|France et ses territoires|3e|zxx|À compléter
France metropoles.png|France · métropoles|Aires urbaines en France|3e|fr|À étudier
France map Lambert-93 topographic.svg|France · relief et grands repères|France et ses territoires|3e|fr|À étudier
Europe relief laea location map.jpg|Europe · relief à compléter|Repères européens|3e|zxx|À compléter
Europe blank political border map.svg|Europe · frontières à compléter|Repères européens|3e|zxx|À compléter
World topography-2002.jpg|Monde · grands reliefs (source 2002)|Habiter la Terre|6e|zxx|À étudier
World Population Density Map 2020.png|Population mondiale · densités (2020)|Population et développement|5e|en|À étudier
Croissant fertile carte.png|Le Croissant fertile|Premiers États et premières écritures|6e|fr|À étudier
Grece antique general.svg|Le monde grec antique|Le monde des cités grecques|6e|fr|À étudier
Map greek sanctuaries-fr.svg|Les sanctuaires du monde grec|Le monde des cités grecques|6e|fr|À étudier
Magna Graecia ancient colonies and dialects-fr.svg|Cités et colonies grecques|Le monde des cités grecques|6e|fr|À étudier
Alexander III empire map-fr.svg|L’empire d’Alexandre|Le monde des cités grecques|6e|fr|À étudier
Roman Empire in 44 BC.png|Rome · territoire en 44 avant J.-C.|Rome et son empire|6e|en|À étudier
Roman Empire in 14 AD.png|Rome · territoire en 14 après J.-C.|Rome et son empire|6e|en|À étudier
Roman Empire Trajan 117AD.png|L’Empire romain sous Trajan (117)|Rome et son empire|6e|en|À étudier
Carte de l’Empire romain en 118 après J.-C.jpg|L’Empire romain · carte de référence (118)|Rome et son empire|6e|fr|À étudier
Muslim Conquest.PNG|L’expansion du monde musulman|Chrétientés et islam au Moyen Âge|5e|en|À étudier
Holy Roman Empire 1000 map-fr.svg|L’Europe et l’Empire vers l’an 1000|Sociétés médiévales|5e|fr|À étudier
Carte de l’Afrique en 1914.svg|L’Afrique coloniale en 1914|Conquêtes et sociétés coloniales|4e|fr|À étudier
Colonisation 1492.png|Colonisations · situation en 1492|Ouverture au monde|5e|zxx|À étudier
Colonisation 1754.png|Empires coloniaux en 1754|Expansions au XVIIIe siècle|4e|zxx|À étudier
Colonisation 1914.png|Empires coloniaux en 1914|Conquêtes et sociétés coloniales|4e|zxx|À étudier
Colonization 1945 français.png|Les empires coloniaux en 1945|Décolonisation|3e|fr|À étudier
Colonisation 1974.png|Décolonisations · situation en 1974|Décolonisation|3e|zxx|À étudier
OrteliusWorldMap1570.jpg|Représenter le monde en 1570 · Ortelius|Grandes découvertes|5e|la|À étudier
Viajes de colon en.svg|Les voyages de Christophe Colomb|Grandes découvertes|5e|en|À étudier
Map Europe alliances 1914-fr.svg|Les alliances européennes en 1914|Première Guerre mondiale|3e|fr|À étudier
Alliances militaires en Europe 1914-1918-fr.svg|Les alliances pendant la Première Guerre mondiale|Première Guerre mondiale|3e|fr|À étudier
Map Europe regimes 1914.png|Les régimes politiques en Europe en 1914|L’Europe avant 1914|4e|fr|À étudier
World War I 1914 08 04.png|La guerre en Europe · août 1914|Première Guerre mondiale|3e|en|À étudier
World War I 1918 05.png|La guerre en Europe · mai 1918|Première Guerre mondiale|3e|en|À étudier
WWII in Europe 1939-1941-fr.svg|La guerre en Europe de 1939 à 1941|Seconde Guerre mondiale|3e|fr|À étudier
Cold War Map 1959.svg|Les blocs dans le monde en 1959|Guerre froide|3e|en|À étudier
Cold war europe military alliances map fr.png|Les alliances militaires en Europe · guerre froide|Guerre froide|3e|fr|À étudier
Cold war europe economic alliances map fr.png|Les organisations économiques européennes · guerre froide|Guerre froide|3e|fr|À étudier
Iron Curtain map.svg|Le rideau de fer en Europe|Guerre froide|3e|en|À étudier
European Coal and Steel Community Map 1952.svg|Les six États de la CECA en 1952|Construction européenne|3e|zxx|À compléter
EU map blank.svg|Union européenne · fond de carte|Construction européenne|3e|zxx|À compléter
Tectonic plates boundaries World map Wt 10degE centered-fr.svg|Les limites des plaques tectoniques|Dynamique de la Terre|Cycle 4|fr|À étudier
Tectonic plates hotspots-fr.svg|Plaques tectoniques et points chauds|Dynamique de la Terre|Cycle 4|fr|À étudier
Map Polynesian migration-fr.svg|Les migrations polynésiennes|Migrations et peuplements|6e|fr|À étudier
Réunion topographic map-fr.svg|La Réunion · relief et repères|France et ses territoires|3e|fr|À étudier
Guadeloupe map-fr.svg|Guadeloupe · repères géographiques|France et ses territoires|3e|fr|À étudier
Martinique map-fr.svg|Martinique · repères géographiques|France et ses territoires|3e|fr|À étudier
French Guiana map-fr.svg|Guyane · repères géographiques|France et ses territoires|3e|fr|À étudier
Mayotte topographic map-fr.svg|Mayotte · relief et repères|France et ses territoires|3e|fr|À étudier'''
items=[]
for row in rows.splitlines():
 name,title,topic,grade,language,use=row.split('|');name=name.replace('’',"'")
 items.append(dict(source_name=name,title=title,topic=topic,grades=[]if grade=='Cycle 4'else[grade],cycle='Cycle 4'if grade=='Cycle 4'else'',language=language,educational_use=use,category='Cartes',subjects=['SVT']if topic=='Dynamique de la Terre'else['Histoire-géographie'],learning_objective=('Compléter les repères et construire une légende à partir du cours.'if use=='À compléter'else'Lire les repères, la légende et la date de la carte pour comprendre le thème : '+topic+'.')))
Path('assets/library/reference/map-selection.json').write_text(json.dumps(items,ensure_ascii=False,indent=2),encoding='utf-8');print(len(items),'map targets; visual/rights approval still required')
