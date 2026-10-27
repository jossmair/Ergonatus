import io,threading,wave
import pytest
from shared.translation_speech import prepare_playback

@pytest.mark.parametrize('rate,channels',[(16000,1),(22050,1),(24000,2),(48000,1)])
def test_device_warmup_preserves_entire_utterance(rate,channels):
    # Audible samples from the first frame to the last expose accidental trimming.
    pcm=b'\x10\x20'*(rate//10)*channels
    data=io.BytesIO()
    with wave.open(data,'wb') as audio:
        audio.setnchannels(channels);audio.setsampwidth(2);audio.setframerate(rate);audio.writeframes(pcm)
    with wave.open(io.BytesIO(prepare_playback(data.getvalue())),'rb') as audio:
        assert (audio.getnchannels(),audio.getsampwidth(),audio.getframerate())==(channels,2,rate)
        result=audio.readframes(audio.getnframes())
    prefix=round(rate*.4)*channels*2;tail=round(rate*.08)*channels*2
    assert result[:prefix]==bytes(prefix)
    assert result[prefix:prefix+len(pcm)]==pcm
    assert result[prefix+len(pcm):]==bytes(tail)

def test_traductor_pace_is_slightly_slower(monkeypatch):
    from shared.translation_speech import speak
    from shared.speech import Speaker
    from ergoai.voice_service import length_scale
    import shared.neural_speech
    seen=[]
    monkeypatch.setattr(shared.neural_speech,'stream',lambda text,voice,rate,*args,**kwargs:seen.append(rate) or True)
    assert speak(Speaker(),'Bonjour','fr')
    assert seen==[0] and 1.05<length_scale(0)/length_scale(1)<1.1
