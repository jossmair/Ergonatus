import threading
from types import SimpleNamespace


def test_correction_keeps_sentence_boundaries_and_line_breaks():
    from ergoai.proofreading_service import Proofreader
    seen=[]
    class Model:
        def create_chat_completion(self,**kwargs):
            source=kwargs['messages'][-1]['content'];seen.append(source)
            yield {'choices':[{'delta':{'content':source},'finish_reason':'stop'}]}
    host=Proofreader();host.engine=SimpleNamespace(stop=threading.Event(),llm=Model())
    source='Hier, je suis allé au magasin. Les prix étaient trop chers.\n\nDemain, je retournerai le chercher.'
    result=host.correct(source,threading.Event())
    assert result['text']==source
    assert seen==['Hier, je suis allé au magasin.','Les prix étaient trop chers.','Demain, je retournerai le chercher.']


def test_dictionary_reaches_common_word_outside_alphabetical_prefix_page():
    from shared.dictionary import lookup
    result=lookup('hipopotame')
    assert not result['found'] and result['suggestions'][0]=='hippopotame'


def test_explicator_low_memory_is_explicit_and_never_solves(monkeypatch):
    import ergoai.learning as learning
    def no_memory(*args):raise ValueError('Mémoire disponible insuffisante pour charger le modèle.')
    monkeypatch.setattr(learning,'lightweight_model',no_memory)
    result=learning.lightweight('Léa a 3 boîtes de 4 billes.',threading.Event(),'Primaire',1)
    assert result['fallback'] and result['model'] is None and 'sans IA' in result['warning']
    assert not any(c.isdigit() for c in result['text']) and 'groupe' in result['text']


def test_explicator_does_not_mask_other_failures(monkeypatch):
    import pytest
    import ergoai.learning as learning
    def invalid(*args):raise ValueError('Empreinte du modèle incorrecte.')
    monkeypatch.setattr(learning,'lightweight_model',invalid)
    with pytest.raises(ValueError,match='Empreinte'):learning.lightweight('Un exercice.',threading.Event(),'Collège',1)


def test_primary_style_survives_repeated_normalization():
    from suite_design import lightify
    css='QPushButton[suitePrimary="true"] {background:#7E2A72;color:#FFFFFF;}'
    assert lightify(css,'#B248AA')==css
    assert lightify(lightify(css,'#B248AA'),'#B248AA')==css


def test_memory_pressure_shortens_idle_residency(monkeypatch):
    import psutil
    from ergoai.memory_budget import idle_timeout
    monkeypatch.setattr(psutil,'virtual_memory',lambda:SimpleNamespace(available=1024**3))
    assert idle_timeout()==20
    monkeypatch.setattr(psutil,'virtual_memory',lambda:SimpleNamespace(available=4*1024**3))
    assert idle_timeout()==90


def test_release_never_interrupts_active_or_queued_work():
    import queue
    from ergoai.memory_budget import release_if_idle
    lock=threading.Lock();jobs=queue.Queue();calls=[]
    lock.acquire()
    assert not release_if_idle(lock,jobs,lambda:calls.append('unloaded'))
    lock.release();jobs.put('waiting')
    assert not release_if_idle(lock,jobs,lambda:calls.append('unloaded'))
    jobs.get()
    assert release_if_idle(lock,jobs,lambda:calls.append('unloaded'))
    assert calls==['unloaded']
