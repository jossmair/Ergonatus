import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

@pytest.fixture
def calculator(tmp_path,monkeypatch):
    app=QApplication.instance() or QApplication([])
    monkeypatch.setenv('ERGONATUS_DATA',str(tmp_path));monkeypatch.setenv('ERGONATUS_NO_HOTKEYS','1')
    from shared.apps.tools import ToolsApplication
    window=ToolsApplication('calculinator');window.show();app.processEvents()
    yield window
    window.closing=True;window.layout_timer.stop();window.orb.close();window.tray.hide();window.server.close();window.records.close();window.close()

def click(window,sequence):
    for label in sequence:QTest.mouseClick(window.keys[label],Qt.LeftButton)

def test_clickable_digits_and_chained_operations(calculator):
    click(calculator,['1','2','+','3','='])
    assert calculator.result.text()=='15'
    click(calculator,['×','2','='])
    assert calculator.result.text()=='30'
    click(calculator,['7'])
    assert calculator.expression.text()=='7'
    assert calculator.calculator_views.currentIndex()==0

def test_history_never_compresses_or_overlaps_the_keypad(calculator):
    app=QApplication.instance();calculator.resize(380,600);app.processEvents();before=calculator.size()
    QTest.mouseClick(calculator.history_toggle,Qt.LeftButton);app.processEvents()
    assert calculator.history.isVisible() and not calculator.keypad.isVisible()
    assert calculator.size()==before
    QTest.mouseClick(calculator.history_toggle,Qt.LeftButton);app.processEvents()
    assert calculator.keypad.isVisible() and not calculator.history.isVisible()
    assert calculator.calculator_views.rect().contains(calculator.keypad.geometry())
    rectangles=[button.geometry() for button in calculator.keys.values()]
    assert all(rect.height()>=44 for rect in rectangles)
    assert all(calculator.keypad.rect().contains(rect) for rect in rectangles)
    assert all(not first.intersects(last) for i,first in enumerate(rectangles) for last in rectangles[i+1:])

def test_decimal_fraction_sign_and_erase(calculator):
    click(calculator,['0',',','1','+','0',',','2','='])
    assert calculator.result.text()=='3 / 10'
    click(calculator,['C','9','⌫','5','±','='])
    assert calculator.result.text()=='-5'
    assert calculator.history.count()==2

def test_error_preserves_expression_and_keyboard_works(calculator):
    click(calculator,['8','÷','0','='])
    assert calculator.expression.text()=='8÷0'
    assert 'zéro' in calculator.status.text()
    click(calculator,['C'])
    calculator.expression.setFocus();QTest.keyClicks(calculator.expression,'(8+4)/3');QTest.keyClick(calculator.expression,Qt.Key_Return)
    assert calculator.result.text()=='4'


def wait_math(window):
    import time
    for _ in range(500):
        QApplication.processEvents();time.sleep(.01)
        if not window.math_busy:return
    assert not window.math_busy

def test_student_panel_buttons_and_exact_algebra(calculator):
    QTest.mouseClick(calculator.student_toggle,Qt.LeftButton);QApplication.processEvents()
    assert calculator.student_panel.isVisible()
    calculator.expression.setText('(x+1)²')
    QTest.mouseClick(calculator.keys['='],Qt.LeftButton);wait_math(calculator)
    assert calculator.result.text()=='x² + 2x + 1'
    QTest.mouseClick(calculator.student_keys['sin'],Qt.LeftButton)
    assert calculator.expression.text()=='sin()' and calculator.expression.cursorPosition()==4
    calculator.expression.insert('30');calculator.compute();wait_math(calculator)
    assert calculator.result.text()=='1/2'
    calculator.expression.setText('(x²-1)/(x-1)');QTest.mouseClick(calculator.keys['='],Qt.LeftButton);wait_math(calculator)
    assert calculator.result.text()=='x + 1' and '≠ 0' in calculator.status.text()
    assert not hasattr(calculator,'angle_unit')
    student_rects=[button.geometry() for button in calculator.student_keys.values()]
    assert all(calculator.student_panel.rect().contains(rect) for rect in student_rects)
    assert all(not first.intersects(last) for i,first in enumerate(student_rects) for last in student_rects[i+1:])
    rectangles=[button.geometry() for button in calculator.keys.values()]
    assert all(calculator.keypad.rect().contains(rect) and rect.height()>=44 for rect in rectangles)
    assert all(not first.intersects(last) for i,first in enumerate(rectangles) for last in rectangles[i+1:])
    QTest.mouseClick(calculator.student_toggle,Qt.LeftButton)
    assert not calculator.student_panel.isVisible() and calculator.preferences['student_mode'] is False

def test_student_fraction_on_main_screen_with_mouse(calculator):
    from PySide6.QtWidgets import QDialog
    QTest.mouseClick(calculator.student_toggle,Qt.LeftButton)
    QTest.mouseClick(calculator.student_keys['a/b'],Qt.LeftButton)
    assert calculator.fraction_editor.isVisible() and not calculator.findChildren(QDialog)
    QApplication.processEvents()
    assert all(button.height()>=44 for button in calculator.keys.values())
    assert calculator.keypad.mapTo(calculator,calculator.keypad.rect().bottomRight()).y()<calculator.calculator_copy_button.mapTo(calculator,calculator.calculator_copy_button.rect().topLeft()).y()
    click(calculator,['1']);QTest.mouseClick(calculator.fraction_fields[1],Qt.LeftButton);click(calculator,['3'])
    QTest.mouseClick(calculator.fraction_confirm,Qt.LeftButton)
    assert calculator.expression.text()=='(1)/(3)'
    click(calculator,['+']);QTest.mouseClick(calculator.student_keys['a/b'],Qt.LeftButton)
    click(calculator,['1']);QTest.mouseClick(calculator.fraction_fields[1],Qt.LeftButton);click(calculator,['6','=']);wait_math(calculator)
    assert calculator.result.text()=='1/2'

def test_nested_fraction_and_cancel_with_mouse(calculator):
    QTest.mouseClick(calculator.student_toggle,Qt.LeftButton)
    QTest.mouseClick(calculator.student_keys['a/b'],Qt.LeftButton)
    click(calculator,['1']);QTest.mouseClick(calculator.fraction_fields[1],Qt.LeftButton)
    QTest.mouseClick(calculator.student_keys['a/b'],Qt.LeftButton)
    click(calculator,['1']);QTest.mouseClick(calculator.fraction_fields[1],Qt.LeftButton);click(calculator,['2','=']);wait_math(calculator)
    assert calculator.result.text()=='2' and not calculator.fraction_active
    QTest.mouseClick(calculator.student_keys['a/b'],Qt.LeftButton);click(calculator,['4','='])
    assert calculator.fraction_active and 'dénominateur' in calculator.status.text()
    QTest.mouseClick(calculator.fraction_cancel,Qt.LeftButton)
    assert not calculator.fraction_active and calculator.expression.isVisible()

def test_stacked_fraction_rendering_and_editing(calculator):
    from PySide6.QtGui import QFont
    from shared.ui.math_display import math_box,MathInput,MathResult
    assert isinstance(calculator.expression,MathInput) and isinstance(calculator.result,MathResult)
    font=QFont('Arial',20)
    fraction=math_box('(x+1)/(2x)',font);number=math_box('2',font)
    assert fraction.height>number.height*1.4
    calculator.student_toggle.setChecked(True);calculator.toggle_student_mode()
    calculator.expression.setText('(1)/(2)+(1)/(3)');calculator.compute();wait_math(calculator)
    calculator.keys['='].setFocus();QApplication.processEvents()
    assert calculator.result.text()=='5/6'
    assert not calculator.expression.hasFocus()
    assert not calculator.expression.grab().isNull() and not calculator.result.grab().isNull()
    assert all(calculator.keypad.rect().contains(button.geometry()) for button in calculator.keys.values())
    keypad_bottom=calculator.keypad.mapTo(calculator,calculator.keypad.rect().bottomRight()).y()
    copy_top=calculator.calculator_copy_button.mapTo(calculator,calculator.calculator_copy_button.rect().topLeft()).y()
    assert keypad_bottom<copy_top
    calculator.expression.setFocus();QTest.keyClick(calculator.expression,Qt.Key_End)
    QTest.keyClicks(calculator.expression,'+1/6');calculator.compute();wait_math(calculator)
    assert calculator.result.text()=='1'

def test_algebra_typography_distinguishes_letter_and_multiplication(calculator):
    from PySide6.QtGui import QFont
    from shared.ui.math_display import math_box,variable_font
    font=QFont('Arial',20);italic=variable_font(font)
    assert italic.italic() and italic.family()=='Times New Roman'
    assert math_box('5*x',font).width<math_box('5*2',font).width
    calculator.student_toggle.setChecked(True);calculator.toggle_student_mode()
    click(calculator,['5']);QTest.mouseClick(calculator.student_keys['x²'],Qt.LeftButton)
    click(calculator,['−','4']);QTest.mouseClick(calculator.student_keys['x'],Qt.LeftButton)
    click(calculator,['+','6','=']);wait_math(calculator)
    assert calculator.result.text()=='5x² - 4x + 6'


def test_rounded_letters_keep_native_editing_selection_and_undo(calculator):
    entry=calculator.expression;entry.setText('9x²+3x²+2x−3y');entry.setFocus();QApplication.processEvents()
    assert entry.font().family()=='Times New Roman' and entry.font().italic()
    entry.setSelection(4,3);assert entry.selectedText()=='3x²'
    QTest.keyClicks(entry,'4x');assert entry.text()=='9x²+4x+2x−3y'
    QTest.keyClick(entry,Qt.Key_Backspace);assert entry.text()=='9x²+4+2x−3y'
    QTest.keyClick(entry,Qt.Key_Z,Qt.ControlModifier);assert entry.text()=='9x²+4x+2x−3y'


def test_fraction_navigation_button_and_compact_block(calculator):
    QTest.mouseClick(calculator.student_toggle,Qt.LeftButton);QTest.mouseClick(calculator.student_keys['a/b'],Qt.LeftButton)
    click(calculator,['1']);QTest.mouseClick(calculator.fraction_next,Qt.LeftButton)
    assert calculator.fraction_target is calculator.fraction_fields[1] and 'haut' in calculator.fraction_next.text()
    click(calculator,['2']);QTest.mouseClick(calculator.fraction_next,Qt.LeftButton)
    assert calculator.fraction_target is calculator.fraction_fields[0]
    click(calculator,['+','1','=']);wait_math(calculator)
    assert calculator.result.text()=='1'
    QTest.mouseClick(calculator.student_keys['a/b'],Qt.LeftButton);QApplication.processEvents()
    assert all(180<=field.width()<=280 for field in calculator.fraction_fields)
    assert calculator.fraction_fields[0].geometry().bottom()<calculator.fraction_fields[1].geometry().top()
