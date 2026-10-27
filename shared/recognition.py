"""Voluntary Windows SAPI closed grammar. No shell commands, no dictation fallback."""
import threading
from PySide6.QtCore import QThread,Signal

class Recognizer(QThread):
    result=Signal(str);error=Signal(str)
    def __init__(self,phrases):super().__init__();self.phrases=phrases;self.stopping=threading.Event()
    def stop(self):self.stopping.set();self.wait(1500)
    def run(self):
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()
        try:
            recognizer=win32com.client.Dispatch('SAPI.SpInprocRecognizer')
            inputs=recognizer.GetAudioInputs()
            if not inputs.Count:raise ValueError('Aucun microphone de reconnaissance Windows disponible.')
            recognizer.AudioInput=inputs.Item(0);context=recognizer.CreateRecoContext();grammar=context.CreateGrammar(1)
            rule=grammar.Rules.Add('ErgonatusCommands',33,1)
            for phrase in self.phrases:rule.InitialState.AddWordTransition(None,phrase)
            grammar.Rules.Commit();grammar.CmdSetRuleState('ErgonatusCommands',1)
            owner=self
            class Events:
                def OnRecognition(self,StreamNumber,StreamPosition,RecognitionType,Result):owner.result.emit(Result.PhraseInfo.GetText())
            sink=win32com.client.WithEvents(context,Events)
            while not self.stopping.wait(.05):pythoncom.PumpWaitingMessages()
            grammar.CmdSetRuleState('ErgonatusCommands',0)
            sink.close()
        except Exception as error:self.error.emit('Reconnaissance Windows indisponible : '+str(error))
        finally:pythoncom.CoUninitialize()
