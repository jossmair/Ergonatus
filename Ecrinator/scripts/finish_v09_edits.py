from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def edit(name,old,new):
 p=ROOT/name;s=p.read_text(encoding='utf-8');assert old in s,(name,old[:80]);p.write_text(s.replace(old,new),encoding='utf-8')
edit('src/ui/tasks.rs','let mut path = self.path.clone();','let path = self.path.clone();')
edit('src/ui/tasks.rs','t.props.style.as_deref()==Some(core::HEADER)','t.props.caption.as_deref()==Some(core::HEADER)')
edit('src/ui/dialogs.rs','        selected: Option<String>,','        selected: Option<String>,\n        topic:String,\n        page:usize,')
edit('src/ui/dialogs.rs','            selected,\n        } = &mut dialog','            selected,topic,page,\n        } = &mut dialog')
edit('src/ui/dialogs.rs','self.library_dialog(ctx, category, query, selected)','self.library_dialog(ctx, category, query, selected,topic,page)')
for name in ['src/ui.rs','src/ui/subject_actions.rs','src/ui/tests.rs']:
 p=ROOT/name;s=p.read_text(encoding='utf-8');import re
 s=re.sub(r'(Dialog::Library\s*\{.*?selected:\s*[^\n]+,)',r'\1\n                        topic:String::new(),page:0,',s,flags=re.S)
 p.write_text(s,encoding='utf-8')
edit('src/ui/tests.rs','    assert!(\n        paths.iter().all(|p| p.is_file()),\n        "Changing type must preserve the previous saved copies"\n    );','    assert!(paths.last().unwrap().is_file());\n    assert!(paths[..paths.len()-1].iter().all(|p|!p.exists()),"Changing type must move the previous file");')
edit('tests/banner_design.rs','fn optional_banner_title_is_editable_roundtrips_and_can_be_cleared()','fn optional_banner_title_is_locked_on_page_but_configurable_and_roundtrips()')
edit('tests/banner_design.rs','    s.run("text.insert", &json!({"text":"Le récit d’aventure"}))\n        .unwrap();','    assert!(s.run("text.insert", &json!({"text":"Interdit"})).is_err());\n    let mut school=School::read(&s.doc);school.title="Le récit d’aventure".into();\n    core::update_header(&mut s,&school).unwrap();')
edit('Cargo.lock','name = "ecrinator"\nversion = "0.8.0"','name = "ecrinator"\nversion = "0.9.0"')
# Direct dependency already available transitively in the offline lockfile.
p=ROOT/'Cargo.lock';s=p.read_text();start=s.index('name = "ecrinator"');end=s.index('\n[[package]]',start);chunk=s[start:end];assert ' "sha2",'not in chunk;chunk=chunk.replace(' "serde_json",',' "serde_json",\n "sha2",');s=s[:start]+chunk+s[end:];p.write_text(s)
