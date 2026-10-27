from pathlib import Path
import json
xs=json.loads(Path('test-output/reference-sources/dore-fable-titles.json').read_text(encoding='utf-8'))
translations='''0|La Cigale et la Fourmi
1|Le Corbeau et le Renard
2|La Grenouille qui veut se faire aussi grosse que le Bœuf
3|Les Deux Mulets
4|Le Loup et le Chien
5|La Génisse, la Chèvre et la Brebis en société avec le Lion
6|La Besace
7|L’Hirondelle et les Petits Oiseaux
8|Le Rat de ville et le Rat des champs
9|L’Homme et son Image
10|Le Dragon à plusieurs têtes et le Dragon à plusieurs queues
11|Le Loup et l’Agneau
12|Les Voleurs et l’Âne
13|La Mort et le Bûcheron
14|Simonide préservé par les Dieux
15|La Mort et le Malheureux
16|Le Loup devenu Berger
17|L’Enfant et le Maître d’école
18|Le Coq et la Perle
19|Les Frelons et les Mouches à miel
20|Le Chêne et le Roseau
21|Contre ceux qui ont le goût difficile
22|Conseil tenu par les Rats
23|Le Loup plaidant contre le Renard devant le Singe
24|L’Homme entre deux âges et ses deux Maîtresses
25|Le Renard et la Cigogne
26|Le Lion et le Moucheron
27|L’Âne chargé d’éponges et l’Âne chargé de sel
28|Le Lion et le Rat
29|La Colombe et la Fourmi
30|L’Astrologue qui se laisse tomber dans un puits
31|Le Lièvre et les Grenouilles
32|Les Deux Taureaux et une Grenouille
33|Le Paon se plaignant à Junon
34|La Chauve-souris et les deux Belettes
35|L’Oiseau blessé d’une flèche
36|Le Meunier, son Fils et l’Âne
37|Le Coq et le Renard
38|Les Grenouilles qui demandent un Roi
39|La Lice et sa Compagne
40|Le Renard et les Raisins
41|L’Aigle et l’Escarbot
42|Le Corbeau voulant imiter l’Aigle
43|Les Loups et les Brebis
44|La Chatte métamorphosée en Femme
45|Philomèle et Progné
46|Le Lion et l’Âne chassant
47|Le Chat et un vieux Rat
48|Testament expliqué par Ésope
49|Le Lion amoureux
50|Le Renard et le Bouc
51|Le Berger et la Mer
52|L’Ivrogne et sa Femme
53|Les Membres et l’Estomac
54|Le Singe et le Dauphin
55|L’Aigle, la Laie et la Chatte
56|L’Avare qui a perdu son trésor
57|La Goutte et l’Araignée
58|L’Œil du Maître
59|Le Loup et la Cigogne
60|Le Lion abattu par l’Homme
61|Le Cygne et le Cuisinier
62|Le Loup, la Chèvre et le Chevreau
63|Le Loup, la Mère et l’Enfant
64|Le Lion devenu vieux
65|La Femme noyée
66|La Belette entrée dans un grenier
67|L’Alouette et ses Petits avec le Maître d’un champ
68|La Mouche et la Fourmi
69|Le Jardinier et son Seigneur
70|Le Bûcheron et Mercure
71|L’Âne et le Petit Chien
72|L’Homme et l’Idole de bois
73|Le Geai paré des plumes du Paon
74|Le Petit Poisson et le Pêcheur
75|Le Combat des Rats et des Belettes
76|Le Chameau et les Bâtons flottants
77|La Grenouille et le Rat
78|La Vieille et les deux Servantes
79|Les Animaux envoyant un tribut à Alexandre
80|Le Cheval s’étant voulu venger du Cerf
81|Le Renard et le Buste
82|Le Cheval et le Loup
83|Parole de Socrate
84|Le Vieillard et ses Enfants
85|L’Oracle et l’Impie
86|La Montagne qui accouche
87|La Fortune et le Jeune Enfant
88|Le Pot de terre et le Pot de fer
89|Les Oreilles du Lièvre
90|Le Renard ayant la queue coupée
91|Le Satyre et le Passant
92|Les Médecins
93|Le Laboureur et ses Enfants
94|La Poule aux œufs d’or
95|L’Âne portant des reliques
96|Le Serpent et la Lime
97|Le Lièvre et la Perdrix
98|Le Cerf et la Vigne
99|Le Lion s’en allant en guerre
100|L’Âne vêtu de la peau du Lion
101|L’Aigle et le Hibou
102|Le Pâtre et le Lion
103|Le Lion et le Chasseur
104|Phébus et Borée
105|L’Ours et les deux Compagnons
106|Jupiter et le Métayer
107|Le Cerf se voyant dans l’eau
108|Le Cochet, le Chat et le Souriceau
109|Le Renard, le Singe et les Animaux
110|Le Mulet se vantant de sa généalogie
111|Le Vieillard et l’Âne
112|Le Villageois et le Serpent
113|Le Lièvre et la Tortue
114|Le Lion malade et le Renard
115|L’Âne et ses Maîtres
116|Le Soleil et les Grenouilles
117|Le Charretier embourbé
119|Le Chien qui lâche sa proie pour l’ombre
120|L’Oiseleur, l’Autour et l’Alouette
121|Le Cheval et l’Âne
122|Le Charlatan
123|La Jeune Veuve
124|La Discorde
125|Les Animaux malades de la peste
126|Le Rat qui s’est retiré du monde
127|Le Héron
128|Le Mal Marié
129|La Fille
130|Les Souhaits
131|Les Vautours et les Pigeons
132|La Cour du Lion
133|La Laitière et le Pot au lait
134|Le Curé et le Mort
135|L’Homme qui court après la Fortune et l’Homme qui l’attend dans son lit
136|Les Deux Coqs
137|Le Coche et la Mouche
138|L’Ingratitude et l’Injustice des hommes envers la Fortune
139|Un Animal dans la Lune
140|Les Devineresses
141|Le Savetier et le Financier
142|Le Chat, la Belette et le Petit Lapin
143|Le Lion, le Loup et le Renard
144|La Tête et la Queue du Serpent
145|Le Chien qui porte à son cou le dîner de son Maître
146|La Mort et le Mourant
147|Le Pouvoir des Fables
148|L’Ours et l’Amateur des jardins
149|L’Homme et la Puce
150|Les Femmes et le Secret
151|Tircis et Amarante
152|Le Rieur et les Poissons
153|Le Rat et l’Huître
154|Les Deux Amis
155|Le Cochon, la Chèvre et le Mouton
156|Le Rat et l’Éléphant
157|Les Obsèques de la Lionne
158|Le Bassa et le Marchand
159|L’Horoscope
160|Le Torrent et la Rivière
161|L’Âne et le Chien
162|Les Deux Chiens et l’Âne mort
163|L’Avantage de la science
164|Le Loup et le Chasseur
165|Jupiter et les Foudres
166|Le Faucon et le Chapon
167|Les Deux Pigeons
168|L’Éducation
169|Le Fou qui vend la Sagesse
170|Le Chat et le Rat
171|Démocrite et les Abdéritains
172|L’Huître et les Plaideurs
173|Le Dépositaire infidèle
174|Jupiter et le Voyageur
175|Le Singe et le Léopard
176|Le Gland et la Citrouille
177|L’Écolier, le Pédant et le Maître d’un jardin
178|Le Chat et le Renard
179|Le Statuaire et la Statue de Jupiter
180|La Souris métamorphosée en Fille
181|Le Singe et le Chat
182|Le Loup et le Chien maigre
183|Le Cierge
184|Rien de trop
185|Les Deux Rats, le Renard et l’Œuf
186|Les Poissons et le Cormoran
187|Le Mari, la Femme et le Voleur
188|Le Berger et le Roi
189|Les Deux Hommes et le Trésor
190|Le Berger et son Troupeau
191|Le Milan et le Rossignol
192|Les Poissons et le Berger qui joue de la flûte
193|L’Homme et la Couleuvre
194|La Tortue et les deux Canards
195|Les Deux Aventuriers et le Talisman
196|L’Avare et son Compagnon
197|Le Loup et les Bergers
198|Les Lapins
199|L’Hirondelle et l’Araignée
200|La Perdrix et les Coqs
201|Le Lion
202|Le Chien à qui on a coupé les oreilles
203|Les Deux Perroquets, le Roi et son Fils
204|Le Paysan du Danube
205|La Lionne et l’Ourse
206|Le Marchand, le Gentilhomme, le Pâtre et le Fils de roi
207|Le Vieillard et les trois Jeunes Hommes
208|Les Dieux voulant instruire un Fils de Jupiter
209|Le Hibou et les Souris
210|Les Compagnons d’Ulysse
211|Le Fermier, le Chien et le Renard
212|Le Songe d’un habitant du Mogol
213|Les Deux Chèvres
214|Le Lion, le Singe et les deux Ânes
215|Le Loup et le Renard
216|Le Cerf malade
217|Le Chat et les deux Moineaux
218|Du Thésauriseur et du Singe
221|Le Vieux Chat et la Jeune Souris
222|La Chauve-souris, le Buisson et le Canard
223|L’Aigle et la Pie
224|La Querelle des Chiens et des Chats, et celle des Chats et des Souris
225|L’Amour et la Folie
226|L’Écrevisse et sa Fille
227|La Forêt et le Bûcheron
228|Le Renard, les Mouches et le Hérisson
229|Le Milan, le Roi et le Chasseur
230|Le Renard et les Poulets d’Inde
231|Le Corbeau, la Gazelle, la Tortue et le Rat
232|Le Renard anglais
233|Le Singe
234|Le Renard, le Loup et le Cheval
235|La Ligue des Rats
236|Un Philosophe scythe
237|Daphnis et Alcimadure
239|L’Éléphant et le Singe de Jupiter
240|Le Fou et le Sage
241|Les Grenouilles et le Soleil
242|Le Juge arbitre, l’Hospitalier et le Solitaire'''
result={xs[int(line.split('|',1)[0])]:line.split('|',1)[1] for line in translations.splitlines()}
Path('assets/library/reference/dore-french-titles.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(len(result),'French fable captions')
