"""Interruptible PCM playback via Windows waveOut, independent of system sounds."""
import ctypes as C
from ctypes import wintypes as W
import io,threading,wave

class Format(C.Structure):
    _fields_=[('tag',W.WORD),('channels',W.WORD),('rate',W.DWORD),('bytes_per_second',W.DWORD),('alignment',W.WORD),('bits',W.WORD),('extra',W.WORD)]
class Header(C.Structure):
    _fields_=[('data',C.c_void_p),('length',W.DWORD),('recorded',W.DWORD),('user',C.c_size_t),('flags',W.DWORD),('loops',W.DWORD),('next',C.c_void_p),('reserved',C.c_size_t)]

class AudioOutput:
    def __init__(self):
        self.api=C.WinDLL('winmm');self.lock=threading.Lock();self.handle=None
        self.api.waveOutOpen.argtypes=[C.POINTER(W.HANDLE),W.UINT,C.POINTER(Format),C.c_size_t,C.c_size_t,W.DWORD];self.api.waveOutOpen.restype=W.UINT
        for name in ('waveOutPrepareHeader','waveOutWrite','waveOutUnprepareHeader'):
            function=getattr(self.api,name);function.argtypes=[W.HANDLE,C.POINTER(Header),W.UINT];function.restype=W.UINT
        for name in ('waveOutReset','waveOutClose'):
            function=getattr(self.api,name);function.argtypes=[W.HANDLE];function.restype=W.UINT
    def stop(self):
        with self.lock:
            if self.handle:self.api.waveOutReset(self.handle)
    def play(self,wav_bytes,stop):
        if stop.is_set():return
        with wave.open(io.BytesIO(wav_bytes),'rb') as source:
            channels,width,rate=source.getnchannels(),source.getsampwidth(),source.getframerate();pcm=source.readframes(source.getnframes())
        if width!=2 or channels not in (1,2):raise ValueError('Format vocal non pris en charge.')
        fmt=Format(1,channels,rate,rate*channels*width,channels*width,width*8,0);handle=W.HANDLE()
        if self.api.waveOutOpen(C.byref(handle),0xFFFFFFFF,C.byref(fmt),0,0,0):raise ValueError('Aucune sortie audio disponible.')
        buffer=C.create_string_buffer(pcm);header=Header();header.data=C.cast(buffer,C.c_void_p);header.length=len(pcm);prepared=False
        with self.lock:self.handle=handle
        try:
            if stop.is_set():return
            if self.api.waveOutPrepareHeader(handle,C.byref(header),C.sizeof(header)):raise ValueError('La sortie audio ne répond pas.')
            prepared=True
            if self.api.waveOutWrite(handle,C.byref(header),C.sizeof(header)):raise ValueError('Lecture audio impossible.')
            while not header.flags&1:
                if stop.wait(.01):self.stop();break
        finally:
            with self.lock:
                self.api.waveOutReset(handle)
                if prepared:self.api.waveOutUnprepareHeader(handle,C.byref(header),C.sizeof(header))
                self.api.waveOutClose(handle);self.handle=None
