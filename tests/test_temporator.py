import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from shared.countdown import Countdown,time_text

def test_countdown_pause_resume_and_finish_once():
    now=[10.];timer=Countdown(lambda:now[0]);timer.configure(65);timer.start();now[0]+=5.25
    assert time_text(timer.remaining())=='01:00'
    timer.pause();now[0]+=100;assert timer.remaining()==59.75
    timer.resume();now[0]+=59.75
    assert timer.tick() and timer.state=='finished' and timer.remaining()==0
    assert not timer.tick()
    timer.reset();assert time_text(timer.remaining())=='01:05'

def test_cycle_skips_missed_periods_without_drifting():
    now=[0.];timer=Countdown(lambda:now[0]);timer.configure(60,20,True);timer.start()
    now[0]=60;assert timer.tick() and timer.phase=='Pause' and timer.remaining()==20
    now[0]=80*10000+85;assert timer.tick() and timer.phase=='Travail' and timer.remaining()==55
    assert not timer.tick()

def test_zero_and_limits_are_validated():
    timer=Countdown()
    for work in (0,-1,6000):
        with pytest.raises(ValueError):timer.configure(work)
    timer.configure(5999,0,False)
    with pytest.raises(ValueError):timer.configure(60,0,True)

@pytest.fixture
def window(tmp_path,monkeypatch):
    app=QApplication.instance() or QApplication([]);monkeypatch.setenv('ERGONATUS_DATA',str(tmp_path));monkeypatch.setenv('ERGONATUS_NO_HOTKEYS','1')
    from shared.apps.timer_widget import TemporatorWindow
    w=TemporatorWindow();w.show();app.processEvents();yield w
    w.cleanup();w.closing=True;w.layout_timer.stop();w.orb.close();w.tray.hide();w.server.close();w.records.close();w.close();app.processEvents()

def test_mouse_duration_and_widget_controls(window):
    w=window;QTest.mouseClick(w.keys['Effacer'],Qt.LeftButton)
    for key in ('2','5'):QTest.mouseClick(w.keys[key],Qt.LeftButton)
    QTest.mouseClick(w.second_button,Qt.LeftButton)
    for key in ('3','0'):QTest.mouseClick(w.keys[key],Qt.LeftButton)
    assert w.work==1530 and w.second_button.text()=='30'
    QTest.mouseClick(w.start_button,Qt.LeftButton)
    assert not w.isVisible() and w.widget.isVisible() and w.model.state=='running'
    QTest.mouseClick(w.widget.play,Qt.LeftButton);assert w.model.state=='paused'
    QTest.mouseClick(w.widget.play,Qt.LeftButton);assert w.model.state=='running'
    QTest.mouseClick(w.widget.reset,Qt.LeftButton);assert w.model.state=='ready' and w.model.remaining()==1530

def test_orb_opens_widget_without_resetting_timer(window):
    w=window;w.start_timer();deadline=w.model.deadline;w.widget.hide();w.orb.activated.emit('temporator')
    assert w.widget.isVisible() and w.model.deadline==deadline
    w.orb.activated.emit('temporator');assert not w.widget.isVisible() and w.model.state=='running' and w.model.deadline==deadline
    w.orb.activated.emit('temporator');assert w.widget.isVisible() and w.model.deadline==deadline
    w.widget.hide()
    w.orb.doubleActivated.emit('temporator');assert w.isVisible()

def test_modes_persistence_and_future_settings(window):
    w=window;w.preset(60);w.start_timer();deadline=w.model.deadline
    w.open_settings();w.preset(300)
    assert w.model.deadline==deadline and w.model.work==60
    assert w.preferences['timer_work']==300
    w.model.pause();w.model.start();assert w.model.work==60

def test_invalid_seconds_and_zero_timer(window):
    w=window;w.select_field('seconds');w.enter('6');w.enter('0')
    assert w.selected_duration()%60==6 and '59' in w.status.text()
    w.enter('Effacer');w.start_timer();assert w.model.state=='ready' and 'durée' in w.status.text()

def test_optional_break_and_finish_without_windows_notification(window,monkeypatch):
    w=window;now=[0.];w.model.clock=lambda:now[0];w.preset(1);events=[]
    monkeypatch.setattr(w.tray,'showMessage',lambda *args:events.append(args));monkeypatch.setattr(QApplication,'beep',lambda:None)
    w.start_timer();now[0]=2;w.tick();w.tick();assert len(events)==0 and w.widget.message.text()=='Temps écoulé' and w.blink_timer.isActive()
    w.cycle.setChecked(True);w.select_kind('rest');w.preset(20);w.start_timer();now[0]=3;w.tick()
    assert w.model.phase=='Pause' and w.model.state=='running' and w.rest==20

def test_widget_paints_and_keyboard_buttons_fit(window):
    w=window;w.activate();QApplication.processEvents()
    image=w.widget.grab().toImage();assert not image.isNull()
    assert w.keys['0'].height()>=37 and w.widget.face.height()>=170
    assert w.keys['⌫'].geometry().bottom()<w.start_button.geometry().bottom()


def test_pause_at_deadline_finishes_and_notifies_once(window,monkeypatch):
    w=window;now=[0.];w.model.clock=lambda:now[0];w.preset(1);events=[]
    monkeypatch.setattr(w.tray,'showMessage',lambda *args:events.append(args));monkeypatch.setattr(QApplication,'beep',lambda:None)
    w.start_timer();now[0]=1;w.toggle_timer();w.tick()
    assert w.model.state=='finished' and len(events)==0 and w.blink_timer.isActive()


def test_settings_survive_restart(window):
    w=window;w.preset(123);w.cycle.setChecked(True);w.select_kind('rest');w.preset(17)
    from shared.domain import Records
    other=Records('temporator')
    try:
        saved=other.all('settings')[0][1]
        assert saved['timer_work']==123 and saved['timer_break']==17 and saved['timer_cycle']
    finally:other.close()

def test_primary_button_has_readable_contrast(window):
    from PySide6.QtGui import QColor,QPalette
    button=window.start_button;QApplication.processEvents();pixmap=button.grab();image=pixmap.toImage();scale=pixmap.devicePixelRatio()
    background=image.pixelColor(round(10*scale),round(button.height()/2*scale));foreground=button.palette().color(QPalette.ButtonText)
    def luminance(color):
        values=[color.redF(),color.greenF(),color.blueF()]
        values=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in values]
        return sum(a*b for a,b in zip(values,(.2126,.7152,.0722)))
    a,b=sorted((luminance(background),luminance(foreground)))
    assert (b+.05)/(a+.05)>=4.5


def test_circle_is_opaque_and_surroundings_transparent(window):
    w=window;w.activate();QApplication.processEvents();pixmap=w.widget.grab();image=pixmap.toImage();scale=pixmap.devicePixelRatio()
    assert image.pixelColor(0,0).alpha()==0
    assert image.pixelColor(image.width()-1,image.height()-1).alpha()==0
    assert image.pixelColor(round(75*scale),round(80*scale)).alpha()==255
    assert w.widget.windowOpacity()==1 and not w.widget.mask().rectCount()
    assert w.widget.reset.y()>=w.widget.face.height() and w.widget.play.y()>=w.widget.face.height()
    assert w.widget.play.text()=='' and not w.widget.play.icon().isNull() and not w.widget.reset.icon().isNull()
    assert w.widget.play.accessibleName()=='Démarrer'
    w.widget.play.click();assert w.widget.play.accessibleName()=='Pause'
    w.widget.play.click();assert w.widget.play.accessibleName()=='Reprendre'
    w.widget.reset.click();assert w.model.state=='ready'

def test_finished_ring_blinks_until_reset_or_restart(window,monkeypatch):
    w=window;now=[0.];w.model.clock=lambda:now[0];w.preset(1)
    monkeypatch.setattr(w.tray,'showMessage',lambda *args:None);monkeypatch.setattr(QApplication,'beep',lambda:None)
    w.start_timer();now[0]=1;w.tick();assert w.blink_timer.isActive() and w.widget.face.flash_on
    w.blink();assert not w.widget.face.flash_on
    w.blink();assert w.widget.face.flash_on
    w.reset_timer();assert not w.blink_timer.isActive()
    w.start_timer();now[0]=2;w.tick();assert w.blink_timer.isActive()
    w.toggle_timer();assert w.model.state=='running' and not w.blink_timer.isActive()

def test_visual_disc_shrinks_and_preserves_running_timer(window):
    w=window;w.clock_timer.stop();now=[0.];w.model.clock=lambda:now[0];w.preset(100);w.start_timer();deadline=w.model.deadline
    w.visual_choice.setChecked(True)
    assert w.visual and w.preferences['timer_visual'] and w.model.deadline==deadline
    areas=[]
    for elapsed in (0,50,100):
        now[0]=elapsed;w.widget.face.update();QApplication.processEvents();image=w.widget.grab().toImage()
        areas.append(sum(image.pixelColor(x,y).name()=='#f3c94f' for x in range(0,image.width(),5) for y in range(0,image.height(),5)))
        assert image.pixelColor(0,0).alpha()==0
    assert areas[0]>areas[1]>areas[2] and areas[2]==0
    assert w.widget.face.accessibleDescription().startswith('00:00')
    w.visual_choice.setChecked(False);assert not w.visual and w.model.deadline==deadline

def test_size_slider_scales_widget_and_keeps_pointer_normal(window):
    w=window;w.show_widget();QApplication.processEvents()
    assert w.widget.width()==200 and w.widget.face.cursor().shape()==Qt.ArrowCursor and w.widget.face.toolTip()==''
    w.start_timer();deadline=w.model.deadline
    for size in (160,280,210):
        w.size_slider.setValue(size);QApplication.processEvents()
        assert w.widget.width()==w.widget.face.height()==size and w.widget.height()>size and w.preferences['timer_size']==size
        assert w.widget.reset.y()>=size and w.widget.play.y()>=size and w.widget.play.geometry().bottom()<w.widget.height()
        assert w.model.deadline==deadline and w.widget.grab().toImage().pixelColor(0,0).alpha()==0
    w.start_timer();assert w.widget.isVisible()


def test_size_slider_thumb_is_not_clipped_and_supports_keyboard(window):
    w=window;slider=w.size_slider;slider.setFocus();QApplication.processEvents()
    for value in (160,220,280):
        slider.setValue(value);QApplication.processEvents();image=slider.grab().toImage()
        rows=[y for y in range(image.height()) for x in range(image.width()) if image.pixelColor(x,y).name()=='#ffd2be']
        assert rows and min(rows)>1 and max(rows)<image.height()-2
    slider.setValue(160);QTest.keyClick(slider,Qt.Key_Right);assert slider.value()==170


def test_controls_stay_below_circle_in_both_presentations(window):
    w=window;w.show_widget()
    for visual in (False,True):
        w.visual_choice.setChecked(visual);QApplication.processEvents()
        assert not w.widget.play.geometry().intersects(w.widget.face.geometry())
        assert not w.widget.reset.geometry().intersects(w.widget.face.geometry())
        assert w.widget.play.y()==w.widget.reset.y()
        assert w.widget.play.x()<w.widget.reset.x()
