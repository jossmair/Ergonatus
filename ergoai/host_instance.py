"""A per-user endpoint owns one language host, even on simultaneous app launches."""
import os,hashlib,atexit

def claim_host(endpoint):
    if os.name!='nt':return True
    import ctypes
    from ctypes import wintypes
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateMutexW.argtypes=[ctypes.c_void_p,wintypes.BOOL,wintypes.LPCWSTR];kernel.CreateMutexW.restype=wintypes.HANDLE
    kernel.CloseHandle.argtypes=[wintypes.HANDLE];kernel.CloseHandle.restype=wintypes.BOOL
    name='Local\\Ergonatus.LanguageHost.'+hashlib.sha256(endpoint.encode()).hexdigest()
    handle=kernel.CreateMutexW(None,True,name)
    if not handle:raise ctypes.WinError(ctypes.get_last_error())
    if ctypes.get_last_error()==183:
        kernel.CloseHandle(handle);return False
    atexit.register(kernel.CloseHandle,handle)
    return True
