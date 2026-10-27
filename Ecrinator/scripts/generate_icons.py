"""Original, deterministic SVG icon family for Écrinator. Development tool only."""
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets'/'school-icons'
OUT.mkdir(parents=True,exist_ok=True)
B='#0757ED'; N='#14264B'; P='#754CC4'; G='#168E67'; O='#F1A000'; R='#E9343B'
icons={}
face=TTFont(ROOT/'assets/fonts/NotoSerif-Variable.ttf')
cmap=face.getBestCmap()
upem=face['head'].unitsPerEm
def add(name,body,color=B):
    icons[name]=f'<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 48 48"><g stroke="{color}" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" fill="none">{body}</g></svg>'
def txt(s,x=24,y=34,size=34,c=N,f='serif',extra=''):
    if s=='♫':
        return f'<g stroke="{c}" fill="{c}"><path d="M17 31V9l23-5v24M17 15l23-5" fill="none" stroke-width="3"/><ellipse cx="11" cy="34" rx="6" ry="4"/><ellipse cx="34" cy="31" rx="6" ry="4"/></g>'
    glyphs=face.getGlyphSet(location={'wght':700 if 'bold' in extra else 400,'wdth':100})
    if any(ord(ch) not in cmap for ch in s):raise ValueError(f'Missing outline in libre font: {s}')
    names=[cmap[ord(ch)] for ch in s]
    scale=size/upem
    left=x-sum(glyphs[n].width for n in names)*scale/2
    paths=[]
    for name in names:
        pen=SVGPathPen(glyphs);glyphs[name].draw(pen)
        paths.append(f'<path d="{pen.getCommands()}" transform="matrix({scale} 0 0 {-scale} {left} {y})" fill="{c}" stroke="none"/>')
        left+=glyphs[name].width*scale
    return ''.join(paths)
add('new','<path d="M13 5h15l9 9v29H13z"/><path d="M28 5v10h9"/>')
add('open','<path d="M4 14V9h14l5 5h20v24H4z" fill="#FFD95A"/><path d="M4 19h40l-5 21H4z" fill="#FFBE15"/>',O)
add('save','<path d="M8 5h27l6 6v32H8z" fill="#8C6BDC"/><path d="M16 5h16v13H16zM15 29h20v14H15z" fill="#FFF"/><path d="M27 9v6M19 34h12"/>',P)
add('edit','<path d="m8 35-2 9 9-2L40 17l-7-7z" fill="#5F9BFF"/><path d="m29 14 7 7m-4-12 4-4 8 8-4 4"/>')
add('undo','<path d="m17 9-11 10 11 10M7 19h21c17 0 16 24-2 24"/>','#2B4F85')
add('redo','<path d="m31 9 11 10-11 10m10-10H20C3 19 4 43 22 43"/>','#8597B0')
add('pdf','<path d="M11 4h20l8 9v31H11z" fill="#F13942"/><path d="M31 4v10h8" stroke="#FFF"/>'+txt('PDF',25,34,12,'#FFF','sans-serif','font-weight="bold"'),R)
add('print','<path d="M14 5h20v12H14zM13 31h22v13H13z" fill="#E2ECFF"/><path d="M13 35H6V17h36v18h-7M18 37h12M18 41h9"/><circle cx="35" cy="23" r="1.5" fill="#0757ED"/>')
add('home','<path d="m5 22 19-17 19 17M10 19v24h28V19M20 43V29h9v14" fill="#D7E7FF"/>')
add('frame','<rect x="6" y="6" width="36" height="36" stroke-dasharray="5 4"/>',N)
add('table','<rect x="5" y="7" width="38" height="34" rx="1" fill="#EEF5FF"/><path d="M5 18h38M5 29h38M18 7v34M31 7v34"/><path d="M6 8h36v9H6z" fill="#91BCF9" stroke="none"/>')
add('image','<rect x="4" y="5" width="40" height="38" rx="3" fill="#EDF6FF"/><path d="m5 34 12-13 10 11 7-7 10 12v6H5z" fill="#3A8CF2"/><circle cx="33" cy="15" r="4" fill="#FFCC38" stroke="#FFBD00"/>')
add('ocr','<path d="M16 5H5v11M32 5h11v11M43 32v11H32M16 43H5V32"/>'+txt('OCR',24,29,15,B,'sans-serif','font-weight="bold"'))
add('formula',txt('π',24,37,43,N))
add('fraction',txt('a',24,18,22,N,'serif','font-style="italic"')+'<path d="M13 24h23" stroke="#14264B"/>'+txt('b',24,43,22,N,'serif','font-style="italic"'))
add('root','<path d="m5 29 7-4 7 15L28 8h16" stroke="#14264B"/>'+txt('x',35,32,24,N,'serif','font-style="italic"'))
add('power',txt('x',21,36,34,N,'serif','font-style="italic"')+txt('2',37,17,18,N))
add('symbol',txt('Ω',24,38,42,N))
add('pi',txt('π',24,37,43,N))
add('angle','<path d="M6 40h38M8 40 28 5M19 40a14 14 0 0 0-5-12"/>',N)
add('figure','<path d="m6 33 14-27 15 27z"/><circle cx="32" cy="32" r="12"/>',N)
add('graph','<path d="M5 5v38h38"/><path d="m10 34 10-14 11 7 10-19"/><circle cx="10" cy="34" r="2.3" fill="#0757ED"/><circle cx="20" cy="20" r="2.3" fill="#0757ED"/><circle cx="31" cy="27" r="2.3" fill="#0757ED"/><circle cx="41" cy="8" r="2.3" fill="#0757ED"/>')
add('results','<rect x="6" y="28" width="8" height="16" rx="1" fill="#317EF5"/><rect x="20" y="17" width="8" height="27" rx="1" fill="#1463ED"/><rect x="34" y="5" width="8" height="39" rx="1" fill="#0757CD"/>')
add('definition','<path d="M16 30c0-5-7-8-7-15a15 15 0 0 1 30 0c0 7-7 10-7 15z" fill="#FFE062"/><path d="M17 36h14M19 41h10M24 1v-3M3 9l-4-3M45 9l4-3M3 23h-5M45 23h5"/>',O)
add('remember','<path d="m3 16 21-11 21 11-21 11z" fill="#6636C1"/><path d="M12 22v14q12 10 24 0V22M43 17v18"/>',P)
add('property','<path d="m19 5 10 0 2 7 7 3 6 5-4 9-7 1-5 7-9-1-3-7-7-3 0-10 7-3z" fill="#C8F1EE"/><circle cx="24" cy="22" r="7"/>','#098C95')
add('method','<circle cx="24" cy="24" r="18"/><circle cx="24" cy="24" r="10"/><circle cx="24" cy="24" r="3" fill="#E9343B"/><path d="m24 24 16-19m-2 0h6v6"/>',R)
add('remark','<circle cx="24" cy="24" r="20" fill="#236DFA"/>'+txt('i',24,36,34,'#FFF','serif','font-weight="bold"'))
add('attention','<path d="m24 3 21 39H3z" fill="#EF3944"/>'+txt('!',24,35,29,'#FFF','sans-serif','font-weight="bold"'),R)
add('example','<path d="m8 35-2 9 9-2 27-27-8-8z" fill="#FFB330"/><path d="m29 12 8 8M8 35l7 7"/>','#ED9100')
add('exercise','<path d="M17 9h26M17 24h26M17 39h26"/><circle cx="6" cy="9" r="3" fill="#0757ED"/><circle cx="6" cy="24" r="3" fill="#0757ED"/><circle cx="6" cy="39" r="3" fill="#0757ED"/>')
add('observation','<path d="M16 30c0-5-7-8-7-15a15 15 0 0 1 30 0c0 7-7 10-7 15z" fill="#BDEAA4"/><path d="M17 36h14M19 41h10M24 3v-3M3 10 0 8M45 10l3-2"/>',G)
add('hypothesis','<path d="M19 3h10M21 3v15L9 39q-2 5 4 5h22q6 0 4-5L27 18V3" fill="#F1E9FF"/><path d="M16 28h16"/><circle cx="21" cy="34" r="2" fill="#9E68DE"/>',P)
add('conclusion','<circle cx="24" cy="24" r="20" fill="#209D6B"/><path d="m13 25 8 8 15-18" stroke="#FFF" stroke-width="4"/>',G)
add('diagram','<path d="m25 7-9 18 20 11M16 25l-9 15"/><circle cx="25" cy="7" r="5" fill="#6FAEFF"/><circle cx="16" cy="25" r="6" fill="#6FAEFF"/><circle cx="36" cy="36" r="6" fill="#6FAEFF"/><circle cx="7" cy="40" r="4" fill="#6FAEFF"/>')
add('legend',txt('A',11,33,29,N,'sans-serif')+'<path d="M26 12h18M26 21h18M26 30h18M26 39h12"/>',N)
add('timeline','<path d="M2 24h44" stroke="#14264B"/><circle cx="9" cy="24" r="5" fill="#EE3039" stroke="#EE3039"/><circle cx="24" cy="24" r="5" fill="#1769EC"/><circle cx="39" cy="24" r="5" fill="#20A26C" stroke="#20A26C"/>')
add('map','<path d="m23 3 9 7 7-1 3 10-7 9 3 14-14 3-6-10-12-3 4-12-4-6 13-2z" fill="#C9E9B8"/>',N)
add('source','<rect x="9" y="3" width="30" height="42" rx="1" fill="#F6F9FF"/><path d="M16 11h16M16 17h16M16 23h16M16 38h16"/><rect x="16" y="27" width="16" height="6" fill="#8CB8F6"/>',N)
add('vocabulary','<path d="M4 9q10-4 20 1 10-5 20-1v31q-10-4-20 1-10-5-20-1z" fill="#DFD2FF"/><path d="M24 11v29M10 18h8M10 25h8M30 18h8M30 25h8"/>',P)
add('folder','<path d="M4 12V7h15l6 6h19v28H4z" fill="#B7EDD0"/><path d="M4 20h40v21H4z" fill="#42B987"/>',G)
add('settings','<path d="m18 4 12 0 2 7 7 3 6 9-4 10-9 2-4 9-11-1-3-9-8-4-2-11 7-5 3-8z" fill="#0757ED"/><circle cx="24" cy="24" r="8" fill="#FFF"/>')
add('units','<rect x="3" y="14" width="42" height="21" fill="#A5D0FF"/><path d="M10 15v10M17 15v7M24 15v10M31 15v7M38 15v10"/>')
add('quote',txt('“',24,43,58,N))
add('music',txt('♫',24,39,43,P,'serif'))
add('headphones','<path d="M6 29V22a18 18 0 0 1 36 0v7"/><rect x="4" y="24" width="9" height="19" rx="4" fill="#DFE7EF"/><rect x="35" y="24" width="9" height="19" rx="4" fill="#DFE7EF"/>',N)
add('note','<path d="M6 5h36v28L30 45H6z" fill="#FFF0B8"/><path d="M30 45V33h12"/>',O)
add('palette','<path d="M24 4C-1 4-2 42 22 44c8 0 1-9 8-10 20 1 17-30-6-30z" fill="#F2F8FF"/><circle cx="13" cy="16" r="3" fill="#1968EC" stroke="none"/><circle cx="24" cy="12" r="3" fill="#18A361" stroke="none"/><circle cx="35" cy="18" r="3" fill="#EE413B" stroke="none"/><circle cx="12" cy="29" r="3" fill="#9655D2" stroke="none"/>',N)
add('search','<circle cx="20" cy="20" r="14"/><path d="m30 30 14 14"/>',N)
add('page','<rect x="9" y="3" width="30" height="42" fill="#F7FAFF"/><path d="M15 12h18M15 19h18M15 26h18M15 33h18"/>')
add('pages','<path d="M14 4h27v34H14z" fill="#D9E9FF"/><path d="M7 10h27v34H7z" fill="#FFF"/>')
add('layout','<rect x="5" y="4" width="38" height="40" fill="#ECF5FF"/><path d="M5 15h38M18 15v29M18 28h25"/>')
add('chapter',txt('1.',23,37,37,N,'sans-serif','font-weight="bold"'))
add('calendar','<rect x="5" y="8" width="38" height="36" rx="3" fill="#F1F6FF"/><path d="M5 19h38M15 3v10M33 3v10M14 27h4M25 27h4M14 35h4M25 35h4"/>')
add('clock','<circle cx="24" cy="24" r="20"/><path d="M24 10v15l10 6"/>')
add('check','<rect x="5" y="5" width="38" height="38" rx="5" fill="#0757ED"/><path d="m13 24 8 8 15-18" stroke="#FFF" stroke-width="4"/>')
add('bold',txt('G',24,37,37,N,'serif','font-weight="bold"'))
add('italic',txt('I',24,37,37,N,'serif','font-style="italic"'))
add('underline',txt('S',24,34,34,N)+'<path d="M11 41h26" stroke="#14264B"/>')
add('textcolor',txt('A',24,33,35,N)+'<path d="M9 42h30" stroke="#F12230" stroke-width="5"/>')
for name,ys,ends in [('alignleft',[9,19,29,39],[41,31,41,31]),('aligncenter',[9,19,29,39],[41,33,41,33]),('alignright',[9,19,29,39],[41,41,41,41]),('alignjustify',[9,19,29,39],[41,41,41,41])]:
    add(name,''.join(f'<path d="M{7 if name!="alignright" else (17 if i%2 else 7)} {y}h{(end-7) if name!="alignright" else (24 if i%2 else 34)}"/>' for i,(y,end)in enumerate(zip(ys,ends))),N)
add('list','<path d="M17 9h27M17 24h27M17 39h27"/><circle cx="6" cy="9" r="2" fill="#14264B"/><circle cx="6" cy="24" r="2" fill="#14264B"/><circle cx="6" cy="39" r="2" fill="#14264B"/>',N)
add('numbered',txt('1',6,14,12,N,'sans-serif')+txt('2',6,29,12,N,'sans-serif')+txt('3',6,44,12,N,'sans-serif')+'<path d="M17 9h27M17 24h27M17 39h27"/>',N)
add('row','<rect x="3" y="9" width="42" height="30"/><path d="M3 19h42M3 29h42M16 9v30M31 9v30"/><path d="M6 30h36v7H6z" fill="#5DA4FF" stroke="none"/>')
add('column','<rect x="3" y="9" width="42" height="30"/><path d="M3 19h42M3 29h42M16 9v30M31 9v30"/><path d="M32 10h11v28H32z" fill="#5DA4FF" stroke="none"/>')
add('focus','<path d="M16 5H5v11M32 5h11v11M43 32v11H32M16 43H5V32"/><circle cx="24" cy="24" r="7"/>')
add('help','<circle cx="24" cy="24" r="20"/>'+txt('?',24,35,32,B,'sans-serif','font-weight="bold"'))
add('zoom','<circle cx="20" cy="20" r="14"/><path d="m30 30 14 14M13 20h14M20 13v14"/>')
add('delete','<path d="M7 12h34M16 12V5h16v7M11 12l3 32h20l3-32M20 20v16M28 20v16"/>',R)
add('close','<path d="m11 11 26 26M37 11 11 37"/>',N)
add('minimize','<path d="M10 27h28"/>',N)
add('maximize','<rect x="10" y="10" width="28" height="28"/>',N)
add('clear-format','<path d="m9 27 17-20q2-3 5-1l12 10q3 2 0 5L25 42H14L5 34z" fill="#EDE3FF"/><path d="m9 27 16 15M25 42h18"/><path d="M4 8h11M9 3v12"/>',P)
add('header','<rect x="4" y="7" width="40" height="34" rx="3" fill="#F7FAFF"/><path d="M4 21h40M19 7v14"/><path d="M24 13h14M24 17h10M11 28h26M11 34h19"/>')
add('blank','<path d="M10 3h20l9 9v33H10z" fill="#FFF"/><path d="M30 3v10h9"/>','#526681')
add('panel','<rect x="4" y="7" width="40" height="34" rx="3" fill="#F7FAFF"/><path d="M30 7v34"/><path d="M34 15h6M34 23h6M34 31h6M10 15h14M10 23h10"/>')
for subject,base,color in [('french','vocabulary',R),('math','fraction',B),('history','timeline',O),('emc','source',P),('english','vocabulary',G),('spanish','vocabulary',O),('german','vocabulary',P),('biology','diagram',G),('physics','hypothesis',B),('technology','settings',B),('art','palette',P),('subject-music','music',P)]:
    icons[subject]=icons[base].replace(B,color)
add('calculation','<rect x="5" y="4" width="38" height="40" rx="10" fill="#EDF4FF"/><path d="M14 16h10m-5-5v10M29 16h8M14 29l9 9m0-9-9 9M29 33h8"/><circle cx="33" cy="28" r="1" fill="#0757ED"/><circle cx="33" cy="38" r="1" fill="#0757ED"/>')
for name,svg in icons.items():(OUT/(name+'.svg')).write_text(svg,encoding='utf-8')
tiles=[]
for index,(name,svg) in enumerate(icons.items()):
    x=(index%8)*110;y=(index//8)*96
    art=svg.split('<g ',1)[1].rsplit('</g>',1)[0]
    tiles.append(f'<g transform="translate({x},{y})"><rect x="3" y="3" width="104" height="90" rx="7" fill="#FFF" stroke="#D7E2F0"/><g transform="translate(31,12)"><g {art}</g></g>{txt(name,55,78,8,N)}</g>')
catalog_height=((len(icons)+7)//8)*96
(ROOT/'assets/icon-catalog.svg').write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="880" height="{catalog_height}" viewBox="0 0 880 {catalog_height}"><rect width="880" height="{catalog_height}" fill="#F1F6FC"/>'+''.join(tiles)+'</svg>',encoding='utf-8')
rows='\n'.join(f'        "{name}" => egui::include_image!("../assets/school-icons/{name}.svg"),' for name in icons)
(ROOT/'src'/'school_icons.rs').write_text('''//! Original scalable Écrinator icon family; generated by scripts/generate_icons.py.
use eframe::egui::{self,Color32,Rect,Pos2,Response,Vec2};
fn source(name:&str)->egui::ImageSource<'static>{match name{
'''+rows+'''
        _=>egui::include_image!("../assets/school-icons/page.svg"),
}}
pub fn paint(ui:&egui::Ui,name:&str,rect:Rect){egui::Image::new(source(name)).fit_to_exact_size(rect.size()).paint_at(ui,rect);}
pub fn button(ui:&mut egui::Ui,name:&str,label:&str,size:Vec2,vertical:bool)->Response{
    let response=ui.add_sized(size,egui::Button::new("").fill(Color32::TRANSPARENT).stroke(egui::Stroke::NONE).corner_radius(5.));
    let r=response.rect;
    let font=egui::FontId::proportional(if vertical{12.5}else{14.});
    let text_height=ui.painter().layout_no_wrap(label.to_owned(),font.clone(),Color32::from_rgb(16,30,66)).size().y;
    let top=if vertical{r.top().min(ui.clip_rect().bottom()-34.-text_height-4.)}else{r.top()};
    let (icon_rect,text_at)=if vertical{(Rect::from_center_size(Pos2::new(r.center().x,top+16.),Vec2::splat(28.)),Pos2::new(r.center().x,top+34.))}else{(Rect::from_center_size(Pos2::new(r.left()+20.,r.center().y),Vec2::splat(25.)),Pos2::new(r.left()+43.,r.center().y))};
    paint(ui,name,icon_rect);
    ui.painter().text(text_at,if vertical{egui::Align2::CENTER_TOP}else{egui::Align2::LEFT_CENTER},label,font,Color32::from_rgb(16,30,66));
    response.widget_info(||egui::WidgetInfo::labeled(egui::WidgetType::Button,ui.is_enabled(),label));focus(ui,&response);response
}
pub fn focus(ui:&egui::Ui,r:&Response){if r.has_focus(){ui.painter().rect_stroke(r.rect.shrink(1.),5.,egui::Stroke::new(2.2,Color32::from_rgb(7,87,237)),egui::StrokeKind::Inside);}}
''',encoding='utf-8')
print(f'{len(icons)} SVG originaux créés dans {OUT}')
