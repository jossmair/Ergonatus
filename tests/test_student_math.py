import pytest
from shared.student_math import solve

@pytest.mark.parametrize('source,action,result',[
    ('(x+1)²','expand','x² + 2x + 1'),
    ('2x+3x-y+y','simplify','5x'),
    ('1/2+1/3','calculate','5/6'),
    ('(x²-1)/(x-1)','simplify','x + 1'),
    ('√(12)','calculate','2×√(3)'),
    ('sin(30)','calculate','1/2'),
    ('cos(60)','calculate','1/2'),
    ('tan(45)','calculate','1'),
    ('0,1+0,2','calculate','3/10'),
    ('(x+y)(x-y)','expand','x² - y²'),
    ('(x+1)²','calculate','x² + 2x + 1'),
    ('(x+y)(x-y)','calculate','x² - y²'),
    ('2x+3x','calculate','5x'),
    ('(x²-1)/(x-1)','calculate','x + 1'),
    ('sin(x)²+cos(x)²','calculate','1'),
    ('5x²-4x+6','calculate','5x² - 4x + 6'),
])
def test_exact_student_examples(source,action,result):
    assert solve(source,action)['text']==result

def test_units_and_domain_are_explicit():
    assert solve('sin(30)')['text']=='1/2'
    assert solve('(x²-1)/(x-1)','simplify')['conditions']=='x - 1 ≠ 0'
    assert solve('√(x²)','simplify')['text']=='abs(x)'
    assert solve('abs(x)')['text']=='abs(x)'

@pytest.mark.parametrize('text',['1/0','tan(90)','√(-1)','x^99','(x^8)^8',
    '__import__("os")','x.__class__','[x]','sin(x,y)','z+1','9'*13])
def test_rejects_invalid_or_unbounded_input(text):
    with pytest.raises(ValueError):solve(text)
