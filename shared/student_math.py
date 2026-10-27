"""Bounded exact school mathematics. User input is never evaluated as Python."""
import ast
import re


def normalized_source(expression):
    if not isinstance(expression,str) or not 0<len(expression)<=160:
        raise ValueError('Expression vide ou trop longue (160 caractères maximum).')
    source=expression.replace('−','-').replace('×','*').replace('÷','/').replace(',','.').replace('²','**2').replace('^','**').replace('√','sqrt').replace('π','pi')
    pattern=r'\d+(?:\.\d+)?|sqrt|abs|sin|cos|tan|pi|x|y|\*\*|[+*/()\-]'
    tokens=re.findall(pattern,source)
    if ''.join(tokens)!=re.sub(r'\s+','',source):
        raise ValueError('Utilisez x, y, des nombres, fractions, racines et sin/cos/tan.')
    parts=[]
    for i,token in enumerate(tokens):
        previous=tokens[i-1] if i else ''
        end=previous in ('x','y','pi',')') or bool(re.fullmatch(r'\d+(?:\.\d+)?',previous))
        start=token in ('x','y','pi','(','sqrt','abs','sin','cos','tan') or bool(re.fullmatch(r'\d+(?:\.\d+)?',token))
        if end and start:parts.append('*')
        parts.append(token)
    return ''.join(parts)


def solve(expression, action='calculate'):
    import sympy as s
    if action not in ('calculate','expand','simplify'):
        raise ValueError('Action inconnue.')
    source=normalized_source(expression)
    try:tree=ast.parse(source,mode='eval')
    except SyntaxError:raise ValueError('Vérifiez les parenthèses et les fractions.') from None
    if len(list(ast.walk(tree)))>65:raise ValueError('Expression trop complexe : séparez le calcul.')
    symbols={name:s.Symbol(name,real=True) for name in ('x','y')};conditions=[]
    def visit(node):
        if isinstance(node,ast.Constant) and type(node.value) in (int,float):
            raw=ast.get_source_segment(source,node)
            if len(raw)>12:raise ValueError('Nombre trop grand.')
            return s.Rational(raw)
        if isinstance(node,ast.Name) and node.id in (*symbols,'pi'):
            return s.pi if node.id=='pi' else symbols[node.id]
        if isinstance(node,ast.UnaryOp) and isinstance(node.op,(ast.UAdd,ast.USub)):
            return visit(node.operand)*(1 if isinstance(node.op,ast.UAdd) else -1)
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and len(node.args)==1 and not node.keywords:
            name=node.func.id;value=visit(node.args[0])
            if name=='abs':return s.Abs(value)
            if name=='sqrt':
                if value.is_negative:raise ValueError('La racine doit être positive ou nulle dans les réels.')
                if value.free_symbols:conditions.append((value,'≥ 0'))
                return s.sqrt(value)
            if name in ('sin','cos','tan'):
                angle=value*s.pi/180
                result={'sin':s.sin,'cos':s.cos,'tan':s.tan}[name](angle)
                if name=='tan' and value.free_symbols:conditions.append((s.cos(angle),'≠ 0'))
                return result
        if isinstance(node,ast.BinOp):
            left,right=visit(node.left),visit(node.right)
            if isinstance(node.op,ast.Add):value=left+right
            elif isinstance(node.op,ast.Sub):value=left-right
            elif isinstance(node.op,ast.Mult):value=left*right
            elif isinstance(node.op,ast.Div):
                if right==0:raise ValueError('Impossible de diviser par zéro.')
                if right.free_symbols:conditions.append((right,'≠ 0'))
                value=left/right
            elif isinstance(node.op,ast.Pow):
                if not right.is_Integer or abs(right)>8:raise ValueError('Puissance entière limitée de −8 à 8.')
                if s.count_ops(left)>15 or left.has(s.Pow):raise ValueError('Puissance trop complexe.')
                if left==0 and right<0:raise ValueError('Impossible de diviser par zéro.')
                if right<0 and left.free_symbols:conditions.append((left,'≠ 0'))
                value=left**right
            else:raise ValueError('Opération non prise en charge.')
            if s.count_ops(value)>100 or any(abs(n)>s.Integer(10)**100 for n in value.atoms(s.Integer)):
                raise ValueError('Expression trop complexe : séparez le calcul.')
            return value
        raise ValueError('Expression non prise en charge.')
    value=visit(tree.body)
    if value.has(s.zoo,s.nan,s.oo,-s.oo) or value.is_real is False:
        raise ValueError('Ce calcul n’a pas de résultat réel défini.')
    if action=='expand':value=s.expand(value)
    elif action=='simplify':value=s.simplify(value)
    else:
        value=s.simplify(value)
        if value.is_polynomial(*symbols.values()):value=s.expand(value)
    if s.count_ops(value)>300:raise ValueError('Résultat trop long à afficher.')
    def display(value):
        text=re.sub(r'\*\*2(?!\d)','²',s.sstr(value)).replace('**','^').replace('sqrt','√').replace('pi','π').replace('Abs','abs')
        text=text.replace('*','×')
        return re.sub(r'(?<=[\dxy²)])×(?=[xy])','',text)
    result=display(value)
    restrictions=list(dict.fromkeys(display(v)+' '+sign for v,sign in conditions))
    return dict(text=result,conditions=' ; '.join(restrictions),action=action)
