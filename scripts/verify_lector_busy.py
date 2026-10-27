from pathlib import Path
import sys,json
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from shared.ui.reading_busy import ReadingBusy
app=QApplication([]);widget=ReadingBusy();widget.begin();frames=[]
for label,phase in [('full',0),('flow',2.3),('turn',4.65)]:
    widget.phase=phase;widget.update();app.processEvents();picture=widget.grab();picture.save(str(root/'docs/validation'/f'lector-hourglass-{label}.png'));frames.append(picture.toImage())
assert frames[0]!=frames[1] and frames[1]!=frames[2]
report=dict(size=[widget.width(),widget.height()],animated_sand=True,turning=True,blocks_input=False,asset=str((root/'assets/lector/hourglass-frame.png').relative_to(root)))
widget.finish();widget.close();(root/'docs/validation/lector-hourglass.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
