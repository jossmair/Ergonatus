"""Read/write the Windows pointer-speed preference, without generating input.

Windows is the source of truth. Never restore or apply a saved speed on launch,
activation, deactivation or exit. Only an explicit slider change writes it.
Reference: https://learn.microsoft.com/windows/win32/api/winuser/nf-winuser-systemparametersinfow
"""
import ctypes as C
from ctypes import wintypes as W
from functools import lru_cache
import sys

SPI_GETMOUSESPEED = 0x0070
SPI_SETMOUSESPEED = 0x0071
SPIF_UPDATEINIFILE = 0x01
SPIF_SENDCHANGE = 0x02


@lru_cache(maxsize=1)
def _api():
    if sys.platform != "win32":
        raise OSError("Le réglage de vitesse nécessite Windows.")
    function = C.WinDLL("user32", use_last_error=True).SystemParametersInfoW
    function.argtypes = [W.UINT, W.UINT, C.c_void_p, W.UINT]
    function.restype = W.BOOL
    return function


def get_speed():
    value = C.c_int()
    if not _api()(SPI_GETMOUSESPEED, 0, C.byref(value), 0):
        raise C.WinError(C.get_last_error())
    if not 1 <= value.value <= 20:
        raise OSError("Vitesse Windows momentanément indisponible.")
    return value.value


def set_speed(value):
    if type(value) is not int or not 1 <= value <= 20:
        raise ValueError("La vitesse Windows doit être comprise entre 1 et 20.")
    # SET expects the integer AS pvParam, not a pointer to an integer.
    if not _api()(SPI_SETMOUSESPEED, 0, C.c_void_p(value), SPIF_UPDATEINIFILE | SPIF_SENDCHANGE):
        raise C.WinError(C.get_last_error())


def speed_label(value):
    return ("Très lente", "Lente", "Normale", "Rapide", "Très rapide")[min(4, max(0, (value - 1) // 4))]
