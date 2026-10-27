"""Native Qt mathematical layout: real fraction bars, without raster assets."""
import ast
from dataclasses import dataclass
from PySide6.QtCore import Qt,QPointF,QRectF,Signal
from PySide6.QtGui import QPainter,QFont,QFontMetricsF,QPalette,QPen
from PySide6.QtWidgets import QLabel,QLineEdit,QStyle,QStyleOptionFrame
from shared.student_math import normalized_source


@dataclass
class Box:
    width:float
    height:float
    baseline:float
    paint:object


def text_box(text,font):
    metrics=QFontMetricsF(font);width=metrics.horizontalAdvance(text)
    def paint(p):p.setFont(font);p.drawText(QPointF(0,metrics.ascent()),text)
    return Box(width,metrics.height(),metrics.ascent(),paint)


def variable_font(font):
    result=QFont(font);result.setFamily('Times New Roman');result.setStyleHint(QFont.Serif);result.setItalic(True)
    return result


def row_box(boxes):
    baseline=max(b.baseline for b in boxes);height=baseline+max(b.height-b.baseline for b in boxes)
    def paint(p):
        x=0
        for box in boxes:
            p.save();p.translate(x,baseline-box.baseline);box.paint(p);p.restore();x+=box.width
    return Box(sum(b.width for b in boxes),height,baseline,paint)


def math_box(source,font):
    tree=ast.parse(normalized_source(source),mode='eval')
    if len(list(ast.walk(tree)))>65:raise ValueError('Expression trop complexe.')
    def visit(node,font):
        text=lambda value:text_box(value,font)
        if isinstance(node,ast.Constant) and type(node.value) in (int,float):return text(str(node.value).replace('.',','))
        if isinstance(node,ast.Name) and node.id in ('x','y','pi'):
            return text('π') if node.id=='pi' else text_box(node.id,variable_font(font))
        if isinstance(node,ast.UnaryOp) and isinstance(node.op,(ast.UAdd,ast.USub)):
            operand=visit(node.operand,font)
            if isinstance(node.operand,ast.BinOp):operand=row_box([text('('),operand,text(')')])
            return row_box([text('−' if isinstance(node.op,ast.USub) else '+'),operand])
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id in ('sin','cos','tan','sqrt','abs') and len(node.args)==1:
            label={'sqrt':'√','abs':'abs'}.get(node.func.id,node.func.id)
            return row_box([text(label+'('),visit(node.args[0],font),text(')')])
        if isinstance(node,ast.BinOp):
            if isinstance(node.op,ast.Div):
                small=QFont(font);small.setPointSizeF(max(11,font.pointSizeF()*.86))
                top=visit(node.left,small);bottom=visit(node.right,small);gap=4;line=top.height+gap
                width=max(top.width,bottom.width)+12;height=top.height+bottom.height+2*gap+1
                def paint(p):
                    p.save();p.translate((width-top.width)/2,0);top.paint(p);p.restore()
                    p.drawLine(QPointF(1,line),QPointF(width-1,line))
                    p.save();p.translate((width-bottom.width)/2,line+gap+1);bottom.paint(p);p.restore()
                return Box(width,height,line+QFontMetricsF(font).xHeight()/2,paint)
            left=visit(node.left,font);right=visit(node.right,font)
            if isinstance(node.op,ast.Pow):
                if isinstance(node.left,ast.BinOp):left=row_box([text('('),left,text(')')])
                small=QFont(font);small.setPointSizeF(max(10,font.pointSizeF()*.65));exponent=visit(node.right,small)
                offset=max(0,exponent.height-left.baseline*.55)
                def paint(p):
                    p.save();p.translate(0,offset);left.paint(p);p.restore()
                    p.save();p.translate(left.width+1,0);exponent.paint(p);p.restore()
                return Box(left.width+exponent.width+1,max(offset+left.height,exponent.height),offset+left.baseline,paint)
            operators={ast.Add:' + ',ast.Sub:' − ',ast.Mult:' × '}
            symbol=operators.get(type(node.op))
            if symbol is None:raise ValueError('Opération inconnue.')
            if isinstance(node.op,ast.Mult):
                def letter(value):
                    return isinstance(value,ast.Name) and value.id in ('x','y') or isinstance(value,ast.BinOp) and isinstance(value.op,ast.Pow) and isinstance(value.left,ast.Name) and value.left.id in ('x','y')
                if letter(node.left) and isinstance(node.right,ast.Constant):left,right=right,left;symbol=''
                elif letter(node.right):symbol=''
                if isinstance(node.left,ast.BinOp) and isinstance(node.left.op,(ast.Add,ast.Sub)):left=row_box([text('('),left,text(')')])
                if isinstance(node.right,ast.BinOp) and isinstance(node.right.op,(ast.Add,ast.Sub)):right=row_box([text('('),right,text(')')])
            if isinstance(node.op,ast.Sub) and isinstance(node.right,ast.BinOp) and isinstance(node.right.op,(ast.Add,ast.Sub)):
                right=row_box([text('('),right,text(')')])
            return row_box([left,text(symbol),right])
        raise ValueError('Expression incomplète.')
    return visit(tree.body,font)


def draw_math(widget,painter,box,area):
    painter.setRenderHint(QPainter.Antialiasing);painter.setRenderHint(QPainter.TextAntialiasing)
    painter.setPen(QPen(widget.palette().color(QPalette.Text),1.3))
    scale=min(1,area.width()/max(1,box.width),area.height()/max(1,box.height))
    painter.translate(area.right()-box.width*scale,area.center().y()-box.height*scale/2);painter.scale(scale,scale);box.paint(painter)


class MathResult(QLabel):
    def paintEvent(self,event):
        font=QFont(self.font());font.setPointSizeF(24)
        try:box=math_box(self.text(),font)
        except (ValueError,SyntaxError,RecursionError):super().paintEvent(event);return
        painter=QPainter(self);draw_math(self,painter,box,QRectF(self.rect()).adjusted(4,3,-4,-3))


class MathInput(QLineEdit):
    """Native editable text on focus; stacked fractions when leaving the field."""
    def __init__(self):
        super().__init__();self.setStyleSheet("QLineEdit {font-family:'Times New Roman';font-style:italic;}");self.textChanged.connect(self.fit_fraction)
    def fit_fraction(self,text):self.setMinimumHeight(54 if '/' in text or '÷' in text else 0)
    def paintEvent(self,event):
        if self.hasFocus() or not any(mark in self.text() for mark in ('/','÷','x','y')):
            super().paintEvent(event);return
        font=QFont(self.font());font.setPointSizeF(18)
        try:box=math_box(self.text(),font)
        except (ValueError,SyntaxError,RecursionError):super().paintEvent(event);return
        painter=QPainter(self);option=QStyleOptionFrame();self.initStyleOption(option)
        self.style().drawPrimitive(QStyle.PE_PanelLineEdit,option,painter,self)
        draw_math(self,painter,box,QRectF(self.rect()).adjusted(12,5,-12,-5))


class FractionField(QLineEdit):
    activated=Signal()
    def focusInEvent(self,event):super().focusInEvent(event);self.activated.emit()
    def mousePressEvent(self,event):super().mousePressEvent(event);self.activated.emit()
