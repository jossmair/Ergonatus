from pathlib import Path
root=Path(__file__).resolve().parents[1]
p=root/'src/ui/dialogs.rs'
s=p.read_text(encoding='utf-8')
a=s.index('                Dialog::Timeline{dates,events}=>{')
b=s.index('                Dialog::Ocr(text)=>{',a)
s=s[:a]+'                Dialog::Timeline(_) | Dialog::Library{..}=>{},\n'+s[b:]
a=s.index('                Dialog::Chart{labels,values}=>{')
b=s.index('                Dialog::Organizer=>{',a)
s=s[:a]+'                Dialog::Chart{..}=>{},\n'+s[b:]
p.write_text(s,encoding='utf-8')
p=root/'src/ui/ribbon.rs';s=p.read_text(encoding='utf-8').replace('("diagram", "Schéma", 10)','("diagram", "Schéma", 29)');p.write_text(s,encoding='utf-8')
p=root/'Cargo.lock';s=p.read_text(encoding='utf-8').replace('name = "ecrinator"\nversion = "0.7.1"','name = "ecrinator"\nversion = "0.8.0"');p.write_text(s,encoding='utf-8')
p=root/'scripts/verify_exports.py';s=p.read_text(encoding='utf-8').replace('112.0','100.0').replace('112.', '100.').replace('102 *', '90 *');p.write_text(s,encoding='utf-8')
