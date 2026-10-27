def luminance(hex_color):
    values=[int(hex_color[i:i+2],16)/255 for i in (1,3,5)]
    values=[x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4 for x in values]
    return sum(a*b for a,b in zip(values,[.2126,.7152,.0722]))
def ratio(a,b):
    first,last=sorted([luminance(a),luminance(b)])
    return (last+.05)/(first+.05)
def test_common_text_and_focus_contrast():
    assert ratio('#F0F5F7','#0D1519')>=7
    assert ratio('#182530','#F2F5F8')>=7
    assert ratio('#3971C4','#FFFFFF')>=3
    assert ratio('#3971C4','#0D1519')>=3
def test_primary_buttons_keep_explicit_keyboard_focus():
    from shared.ui.theme import accent_button_style
    assert 'QPushButton:focus' in accent_button_style('#81E2C6')
