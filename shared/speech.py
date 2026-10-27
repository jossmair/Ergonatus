import threading
import time
import re

def available_voices():
    from ergoai.voice_models import installed_voices
    voices=installed_voices()
    import pythoncom,win32com.client
    pythoncom.CoInitialize()
    try:return voices+[voice.GetDescription() for voice in win32com.client.Dispatch('SAPI.SpVoice').GetVoices()]
    except Exception:
        if voices:return voices
        raise
    finally:pythoncom.CoUninitialize()

class Speaker:
    def __init__(self):self.stop=threading.Event();self.audio=None
    def speak(self,text,rate=0,voice='',on_segment=None,gentle=False):
        from ergoai.voice_models import VOICES
        if voice in VOICES:
            from shared.neural_speech import stream
            from shared.audio_output import AudioOutput
            if self.audio is None:self.audio=AudioOutput()
            return stream(text,voice,rate,self.stop,on_segment,lambda data:self.audio.play(data,self.stop))
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()
        try:
            speaker=win32com.client.Dispatch('SAPI.SpVoice');speaker.Rate=max(-5,min(5,rate-(2 if gentle else 0)))
            if voice:
                matches=[v for v in speaker.GetVoices() if voice.casefold() in v.GetDescription().casefold()]
                if matches:speaker.Voice=matches[0]
            if self.stop.is_set():return False
            parts=re.split(r'\n\s*\n',text) if gentle else [text]
            for index,paragraph in enumerate(part for part in parts if part.strip()):
                if self.stop.is_set() or (index and self.stop.wait(1.15)):break
                if on_segment:on_segment(paragraph)
                speaker.Speak(re.sub(r'(?<!\n)\n(?!\n)',' ',paragraph),1)
                while not speaker.WaitUntilDone(50):
                    if self.stop.is_set():speaker.Speak('',3);break
            return not self.stop.is_set()
        finally:pythoncom.CoUninitialize()
    def cancel(self):
        self.stop.set()
        if self.audio:self.audio.stop()
