"""Physical-pixel layered surface, painted with Qt into a reusable Win32 DIB.

Using a native top-level surface avoids Qt's rounding at mixed-DPI boundaries.
The OS cursor is kept unchanged above the overlay. No cursor is drawn twice.
"""
import ctypes as C
from ctypes import wintypes as W
import math

import numpy as np
from PySide6.QtCore import QRectF
from PySide6.QtGui import QImage, QPainter

DIAMETER = 220


def radial_alpha(diameter=DIAMETER, feather=25):
    yy, xx = np.mgrid[:diameter, :diameter]
    radius = np.hypot(xx + .5 - diameter / 2, yy + .5 - diameter / 2)
    value = np.clip((diameter / 2 - radius) / feather, 0, 1)
    return np.rint(255 * value * value * (3 - 2 * value)).astype(np.uint8)


class BitmapInfo(C.Structure):
    _fields_ = [("size", W.DWORD), ("width", W.LONG), ("height", W.LONG),
                ("planes", W.WORD), ("bits", W.WORD), ("compression", W.DWORD),
                ("image_size", W.DWORD), ("xppm", W.LONG), ("yppm", W.LONG),
                ("used", W.DWORD), ("important", W.DWORD)]


class Blend(C.Structure):
    _fields_ = [("op", C.c_ubyte), ("flags", C.c_ubyte), ("alpha", C.c_ubyte), ("format", C.c_ubyte)]


def paint_lens(destination, source, zoom, mask, source_offset=(0, 0)):
    destination.fill(0)
    painter = QPainter(destination)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    diameter = destination.width()
    span = diameter / zoom
    crop = QRectF(source.width() / 2 + source_offset[0] - span / 2,
                  source.height() / 2 + source_offset[1] - span / 2, span, span)
    painter.drawImage(QRectF(0, 0, diameter, diameter), source, crop)
    painter.setCompositionMode(QPainter.CompositionMode_DestinationIn)
    painter.drawImage(0, 0, mask)
    painter.end()


class MagnifierOverlay:
    def __init__(self, desktop, diameter=DIAMETER):
        self.diameter = diameter
        self.desktop = desktop
        self.user = desktop.user
        self.gdi = C.WinDLL("gdi32", use_last_error=True)
        self.hwnd = self.dc = self.bitmap = self.old_bitmap = None
        self.visible = False
        self.user.CreateWindowExW.argtypes = [W.DWORD, W.LPCWSTR, W.LPCWSTR, W.DWORD, C.c_int, C.c_int, C.c_int, C.c_int, W.HWND, W.HMENU, W.HINSTANCE, C.c_void_p]
        self.user.CreateWindowExW.restype = W.HWND
        self.user.UpdateLayeredWindow.argtypes = [W.HWND, W.HDC, C.POINTER(W.POINT), C.POINTER(W.SIZE), W.HDC, C.POINTER(W.POINT), W.DWORD, C.POINTER(Blend), W.DWORD]
        self.user.UpdateLayeredWindow.restype = W.BOOL
        self.user.ShowWindow.argtypes = [W.HWND, C.c_int]
        self.user.DestroyWindow.argtypes = [W.HWND]
        self.gdi.CreateCompatibleDC.argtypes = [W.HDC]
        self.gdi.CreateCompatibleDC.restype = W.HDC
        self.gdi.CreateDIBSection.argtypes = [W.HDC, C.POINTER(BitmapInfo), W.UINT, C.POINTER(C.c_void_p), W.HANDLE, W.DWORD]
        self.gdi.CreateDIBSection.restype = W.HBITMAP
        self.gdi.SelectObject.argtypes = [W.HDC, W.HANDLE]
        self.gdi.SelectObject.restype = W.HANDLE
        self.gdi.DeleteObject.argtypes = [W.HANDLE]
        self.gdi.DeleteDC.argtypes = [W.HDC]
        try:
            # WS_POPUP; WS_EX_TOOLWINDOW | LAYERED | TRANSPARENT | NOACTIVATE.
            self.hwnd = self.user.CreateWindowExW(0x80800A0, "STATIC", "Précisionator · Loupe", 0x80000000, 0, 0, diameter, diameter, None, None, None, None)
            if not self.hwnd:
                raise C.WinError(C.get_last_error())
            desktop.protect_overlay(self.hwnd)
            self.dc = self.gdi.CreateCompatibleDC(None)
            info = BitmapInfo(C.sizeof(BitmapInfo), diameter, -diameter, 1, 32, 0, diameter * diameter * 4, 0, 0, 0, 0)
            bits = C.c_void_p()
            self.bitmap = self.gdi.CreateDIBSection(self.dc, C.byref(info), 0, C.byref(bits), None, 0)
            if not self.bitmap or not bits.value:
                raise C.WinError(C.get_last_error())
            self.old_bitmap = self.gdi.SelectObject(self.dc, self.bitmap)
            self.buffer = (C.c_ubyte * (diameter * diameter * 4)).from_address(bits.value)
            self.image = QImage(self.buffer, diameter, diameter, diameter * 4, QImage.Format_ARGB32_Premultiplied)
            self.mask_array = np.zeros((diameter, diameter, 4), np.uint8)
            self.mask_array[:, :, 3] = radial_alpha(diameter)
            self.mask = QImage(self.mask_array.data, diameter, diameter, diameter * 4, QImage.Format_ARGB32_Premultiplied)
        except Exception:
            self.close()
            raise

    def render(self, request, source, source_offset=(0, 0)):
        paint_lens(self.image, source, request.zoom, self.mask, source_offset)
        destination = W.POINT(request.x - self.diameter // 2, request.y - self.diameter // 2)
        size, origin = W.SIZE(self.diameter, self.diameter), W.POINT(0, 0)
        blend = Blend(0, 0, max(0, min(255, round(255 * request.opacity))), 1)
        if not self.user.UpdateLayeredWindow(self.hwnd, None, C.byref(destination), C.byref(size), self.dc, C.byref(origin), 0, C.byref(blend), 2):
            raise C.WinError(C.get_last_error())
        if not self.visible:
            self.user.SetWindowPos(self.hwnd, W.HWND(-1), 0, 0, 0, 0, 0x1 | 0x2 | 0x10 | 0x40)
            self.visible = True

    def hide(self):
        if self.hwnd:
            self.user.ShowWindow(self.hwnd, 0)
        self.visible = False

    def close(self):
        self.hide()
        if self.hwnd:
            self.user.DestroyWindow(self.hwnd)
            self.hwnd = None
        if self.dc and self.old_bitmap:
            self.gdi.SelectObject(self.dc, self.old_bitmap)
        if self.bitmap:
            self.gdi.DeleteObject(self.bitmap)
            self.bitmap = None
        if self.dc:
            self.gdi.DeleteDC(self.dc)
            self.dc = None
