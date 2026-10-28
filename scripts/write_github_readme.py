"""Build the GitHub presentation with local, accessible screenshots and icons."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from shared.ui.theme import APP_THEMES
def shot(name,alt,width=1200):return f'<a href="docs/media/{name}.png"><img src="docs/media/{name}.png" alt="{alt}" width="{width}"></a>'
def pair(items):
    return '<table><tr>'+''.join(f'<td width="50%" valign="top"><h3>{title}</h3><p>{copy}</p>'+shot(name,alt,360)+'</td>' for title,copy,name,alt in items)+'</tr></table>\n'
text='''<div align="center">

<a href="https://github.com/jossmair/Ergonatus/releases/latest"><img src="docs/media/ergonatus-banner.png" alt="Ergonatus — Vos outils. À votre rythme. 21 outils Windows pour apprendre, communiquer et s’organiser." width="1280"></a>

### Une suite pour apprendre, s’exprimer et gagner en autonomie.

**Choisissez les aides qui vous sont utiles. Retrouvez-les dans un seul hub.**

Pour les élèves, les familles, les enseignants et les personnes qui les accompagnent.

<a href="#installation-windows"><img src="docs/media/download-installer.png" alt="Installer la suite" width="244"></a>&nbsp;&nbsp;<a href="#version-portable"><img src="docs/media/download-portable.png" alt="Choisir la version portable" width="244"></a>

[Découvrir les outils](#21-outils-à-composer-selon-vos-besoins) · [Voir les téléchargements](https://github.com/jossmair/Ergonatus/releases/latest) · [Construire depuis les sources](BUILDING.md)

</div>

---

<table><tr>
<td width="33%" valign="top"><h3>Votre sélection</h3><p>Activez vos outils, personnalisez votre profil et retrouvez vos aides dans leurs petites Orbs flottantes.</p></td>
<td width="33%" valign="top"><h3>Sur votre ordinateur</h3><p>Les moteurs d’IA, les voix et le dictionnaire sont fournis dans la distribution. Aucun compte Ergonatus à créer.</p></td>
<td width="33%" valign="top"><h3>Des usages concrets</h3><p>Écrire un cours, écouter un texte, exprimer un besoin, comprendre une consigne ou préparer sa semaine.</p></td>
</tr></table>

## Un point d’entrée. Vos outils à portée de clic.

Un clic sur l’Orb d’Ergonatus affiche le catalogue. Chaque outil garde **son nom, sa couleur et sa fonction** : choisissez, lancez, retrouvez.

'''+shot('catalogue','Le catalogue Ergonatus avec les 21 logiciels, leurs noms, leurs icônes et leurs fonctions.',1340)+'''

<p align="center"><sub>Vraies interfaces de la version v2026.10.27, avec des exemples de démonstration. Cliquez sur une capture pour l’agrandir.</sub></p>

## Écrire, lire et mettre ses idées en forme

### Écrinator — des cours dans lesquels on se repère

Matières, bandeaux, encadrés et formules : construisez des documents scolaires avec des repères visuels. Retrouvez vos cours et exportez vos documents.

'''+shot('ecrinator','Écrinator avec un cours de mathématiques et les encadrés Définition, Propriété et Remarque.',1920)+'\n\n'
text+=pair([
 ('Corrector · garder le fil de ses idées','Le texte envoyé à gauche, la proposition corrigée à droite. Sélectionnez, relisez et copiez la réponse dans une interface de discussion.','corrector','Corrector : deux exemples de textes et leurs propositions corrigées, avec copie par réponse.'),
 ('Communicator · trouver comment le dire','Des cartes pour exprimer ses besoins et ses choix. Préparez un message, montrez-le en grand ou faites-le lire à voix haute.','communicator','Communicator : cartes de communication et message J’ai besoin d’un peu de temps pour répondre.')])
text+='\n## Comprendre et s’entraîner, une étape à la fois\n\n'
text+=pair([
 ('Explicator · une piste pour avancer','Capturez une consigne ou collez un énoncé. Demandez une explication et des indices pour chercher par vous-même.','explicator','Explicator : exemple d’indices pédagogiques pour comprendre une fraction d’une quantité.'),
 ('Tablinator · cliquer, retourner, retenir','Toutes les tables de 1 à 12 dans une grille. Cliquez sur une opération pour retourner sa carte et découvrir le résultat.','tablinator','Tablinator : grille des tables de multiplication avec plusieurs cartes retournées.')])
text+='''
## Une semaine plus facile à retrouver

**Planinator** réunit les activités, les cours et les devoirs. Le mode élève donne une couleur à chaque matière ; l’Orb permet de retrouver le widget d’aujourd’hui et de demain.

'''+shot('planinator','Planinator en mode élève avec une semaine de devoirs de démonstration et le jour courant mis en valeur.',1080)+'''

<details>
<summary><strong>Voir aussi : post-it, traduction, dictionnaire et calculatrice</strong></summary>
<br>

'''
for title,copy,name in [
 ('Memorinator — poser une idée, la retrouver plus tard','Un mur de post-it datés, colorés et déplaçables. Ajoutez vos notes, surlignez, barrez et ajustez l’opacité du fond.','memorinator'),
 ('Traductor — une discussion dans deux langues','Choisissez les langues, écrivez votre message, puis écoutez ou copiez la traduction depuis sa bulle.','traductor'),
 ('Dictionnator — les mots et leurs sens','Un dictionnaire français local, avec définitions et suggestions pendant la saisie.','dictionnator'),
 ('Calculinator — des nombres aux expressions','Un clavier à la souris, un historique et un mode élève pour les fractions et le calcul symbolique.','calculinator')]:
    text+='### '+title+'\n\n'+copy+'\n\n'+shot(name,title+' — exemple de démonstration.',1000)+'\n\n'
text+='''</details>

## 21 outils à composer selon vos besoins

<details>
<summary><strong>Explorer le catalogue complet</strong></summary>
<br>

| Outil | Pour quoi faire ? |
|:---|:---|
'''
order=['ecrinator','redactor','corrector','transcrinator','scanator','lector','pdfinator','traductor','dictionnator','explicator','calculinator','tablinator','communicator','planinator','memorinator','organisator','applinator','claviernator','precisionator','concentrator','temporator']
assert set(order)==set(APP_THEMES)-{'ergonatus'}
for key in order:
    item=APP_THEMES[key];text+=f'| <img src="docs/media/icons/{key}.png" width="26" alt=""> **{item["name"]}** | {item["description"]} |\n'
text+='''
</details>

## Prêt à choisir vos outils ?

**Deux formats, la même suite complète. Choisissez celui qui vous convient.**

Les voix, les modèles d’IA et le dictionnaire sont inclus. Les téléchargements sont donc volumineux et découpés en plusieurs fichiers.

### Installation Windows

1. Ouvrez les **[téléchargements de la dernière version](https://github.com/jossmair/Ergonatus/releases/latest)**.
2. Prenez **`Ergonatus-…-Setup.exe` et tous les fichiers `Ergonatus-…-Setup-*.bin`**.
3. Placez-les dans le même dossier et ouvrez **Setup.exe**.

### Version portable

1. Ouvrez les **[téléchargements de la dernière version](https://github.com/jossmair/Ergonatus/releases/latest)**.
2. Prenez **tous les volumes `Ergonatus-…-portable.zip.001`, `.002`, etc.**, ainsi que **`7za.exe`** et **`Extraire-portable.cmd`**.
3. Placez-les dans le même dossier, ouvrez **Extraire-portable.cmd**, puis **Portable → Ergonatus → Lancer Ergonatus.cmd**.

> Gardez tous les sous-dossiers de la suite. Aucun Python installé n’est nécessaire pour utiliser les téléchargements prêts à l’emploi.

### Les premiers pas

**Ouvrez le hub → choisissez votre profil → activez vos outils → retrouvez leurs Orbs.**

Le clic droit ouvre le menu de chaque Orb. Son aide précise ses gestes et ses raccourcis. Quitter Ergonatus arrête les applications de la suite.

<details>
<summary><strong>Informations utiles, sources et licences</strong></summary>
<br>

- **Plateforme :** Windows 10/11 x64.
- **Ressources :** les modèles et voix sont fournis ; l’OCR dépend des langues Windows installées.
- **Stockage :** prévoyez de la place pour les volumes et la suite extraite, d’environ 11 Go pour la version illustrée.
- **Données :** les outils récents utilisent `Data` avec le lanceur portable. Certaines préférences historiques restent dans leur emplacement Windows habituel.
- **IA :** les corrections, traductions et explications sont des propositions à relire.
- **Sélections :** le remplacement automatique dépend de la compatibilité de l’application cible ; la copie reste disponible.
- **Windows :** les exécutables ne sont pas signés ; un avertissement de réputation peut apparaître.
- **Intégrité :** les téléchargements sont accompagnés de `SHA256SUMS.txt`.
- **Développement :** voir [BUILDING.md](BUILDING.md). Les ressources volumineuses sont distribuées séparément des sources.
- **Licences :** chaque composant conserve sa licence. Les notices sont fournies dans ses dossiers ; le dictionnaire dérive du Wiktionnaire via Kaikki.
- **Visuels :** voir les [informations sur les captures](docs/media/README.md).

</details>

---

<p align="center"><strong>ERGONATUS</strong><br>Vos outils. À votre rythme.<br><a href="https://github.com/jossmair/Ergonatus/releases/latest">Télécharger la suite</a> · <a href="https://github.com/jossmair/Ergonatus/issues">Poser une question ou signaler un problème</a></p>
'''
(ROOT/'README.md').write_text(text,encoding='utf-8')
(ROOT/'docs/media/README.md').write_text('''# Visuels de présentation

Captures réalisées le 28 octobre 2026 pour illustrer `v2026.10.27`.

- Les captures Qt représentent les interfaces réelles : les composants utilisés ont été comparés aux sources publiées avant capture.
- Écrinator est capturé depuis l’exécutable livré, avec le document « Encadrés » généré par son mode de vérification.
- Les messages, notes et devoirs sont des exemples créés pour la présentation. Les échanges de correction, explication et traduction illustrent l’interface, pas une mesure de qualité des moteurs.
- Les définitions de Dictionnator proviennent du dictionnaire local et le calcul utilise le calculateur de l’application.
- Aucune capture ne contient de document personnel ni le bureau de l’utilisateur. Les captures ne sont pas des interfaces générées par IA.
- La bannière et les boutons sont des visuels vectoriels rendus en PNG avec les icônes existantes de la suite.

Génération : `scripts/capture_github_showcase.py`, `scripts/create_github_brand.py`, `scripts/write_github_readme.py`.
''',encoding='utf-8')
print('GitHub README generated.')
