"""Deterministic application logic. No UI, AI, shell execution or destructive actions."""
import ast
from fractions import Fraction
from pathlib import Path
import sqlite3
import json
import datetime as dt
import math
import os
import shutil

def app_data(app_id):
    root=Path(os.environ.get('ERGONATUS_DATA',str(Path(os.environ.get('LOCALAPPDATA',Path.home()))/'Ergonatus')))/app_id
    root.mkdir(parents=True,exist_ok=True)
    return root

class Records:
    def __init__(self, app_id, root=None):
        self.path=(Path(root) if root else app_data(app_id))/'records.sqlite3'
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(self.path)
        self.db.execute('CREATE TABLE IF NOT EXISTS records (id INTEGER PRIMARY KEY, kind TEXT NOT NULL, data TEXT NOT NULL)')
        self.db.commit()
    def add(self,kind,data):
        cursor=self.db.execute('INSERT INTO records(kind,data) VALUES(?,?)',(kind,json.dumps(data,ensure_ascii=False)))
        self.db.commit(); return cursor.lastrowid
    def all(self,kind):
        return [(key,json.loads(data)) for key,data in self.db.execute('SELECT id,data FROM records WHERE kind=? ORDER BY id',(kind,))]
    def update(self,key,kind,data):
        self.db.execute('UPDATE records SET data=? WHERE id=? AND kind=?',(json.dumps(data,ensure_ascii=False),key,kind));self.db.commit()
    def close(self): self.db.close()

def calculate(expression):
    if not isinstance(expression,str) or len(expression)>300: raise ValueError('Calcul trop long.')
    expression=expression.replace(',','.').replace('×','*').replace('÷','/').replace('−','-')
    tree=ast.parse(expression,mode='eval')
    if len(list(ast.walk(tree)))>100: raise ValueError('Calcul trop complexe.')
    def visit(node):
        if isinstance(node,ast.Constant) and type(node.value) in (int,float):
            value=Fraction(ast.get_source_segment(expression,node))
        elif isinstance(node,ast.UnaryOp) and isinstance(node.op,(ast.UAdd,ast.USub)):
            value=visit(node.operand)*(1 if isinstance(node.op,ast.UAdd) else -1)
        elif isinstance(node,ast.BinOp):
            left,right=visit(node.left),visit(node.right)
            if isinstance(node.op,ast.Add): value=left+right
            elif isinstance(node.op,ast.Sub): value=left-right
            elif isinstance(node.op,ast.Mult): value=left*right
            elif isinstance(node.op,ast.Div): value=left/right
            elif isinstance(node.op,ast.Pow) and right.denominator==1 and abs(right.numerator)<=100: value=left**int(right)
            else: raise ValueError('Opération non prise en charge.')
        else: raise ValueError('Utilisez des nombres, parenthèses et + − × ÷ ** uniquement.')
        if value.numerator.bit_length()>16000 or value.denominator.bit_length()>16000: raise ValueError('Résultat trop grand.')
        return value
    return visit(tree.body)

def next_review(card,remembered,today=None):
    today=today or dt.date.today()
    successes=int(card.get('successes',0))+1 if remembered else 0
    days=min(365,2**min(successes,9)) if remembered else 1
    return dict(card,successes=successes,due=(today+dt.timedelta(days=days)).isoformat())

FOLDER_TEMPLATES={
    'École':['Français','Mathématiques','Histoire-géographie','Sciences','Langues','À terminer'],
    'Personnel':['Administratif','Santé','Projets','À classer'],
    'Travail':['Documents','Réunions','À traiter','Archives'],
}
def folder_plan(root,template):
    if not str(root).strip():raise ValueError('Choisissez explicitement un dossier parent.')
    root=Path(root).resolve()
    if template not in FOLDER_TEMPLATES or not root.is_dir(): raise ValueError('Choisissez un dossier existant et un modèle.')
    return [root/name for name in FOLDER_TEMPLATES[template] if not (root/name).exists()]
def create_folders(root,template):
    plan=folder_plan(root,template)
    for path in plan: path.mkdir(exist_ok=True)
    return plan

def atomic_text(path,text):
    path=Path(path)
    if path.exists(): shutil.copy2(path,path.with_name(path.name+'.bak'))
    temp=path.with_name(path.name+'.tmp')
    temp.write_text(text,encoding='utf-8');temp.replace(path)

