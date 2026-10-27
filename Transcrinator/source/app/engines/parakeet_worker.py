"""Native ABI runs outside the UI process. IPC carries audio in memory only."""

import ctypes
import json
import os
from contextlib import ExitStack

import numpy as np

from app.engines.native_library import library_directories, missing_cuda_libraries, shutdown_backend
from app.engines.recognition_vocabulary import NativeRecognitionVocabulary


def worker(connection, dll_path, model_path, backend, phrases=()):
    os.environ["PARAKEET_DEVICE"] = backend
    with open(os.devnull, "w") as null:
        os.dup2(null.fileno(), 2)  # native libraries can otherwise log recognized text
    dll_dirs = ExitStack()
    dll = None
    ctx = None
    try:
        if backend.startswith("CUDA"):
            missing = missing_cuda_libraries(dll_path)
            if missing:
                raise RuntimeError(
                    "Dépendances CUDA 12 absentes : " + ", ".join(missing)
                    + ". Réinstallez la version complète de Transcrinator."
                )
        for folder in library_directories(dll_path):
            dll_dirs.enter_context(os.add_dll_directory(str(folder)))
        dll = ctypes.CDLL(dll_path)
        ptr = ctypes.c_void_p
        dll.parakeet_capi_load.argtypes = [ctypes.c_char_p]
        dll.parakeet_capi_load.restype = ptr
        dll.parakeet_capi_free.argtypes = [ptr]
        dll.parakeet_capi_last_error.argtypes = [ptr]
        dll.parakeet_capi_last_error.restype = ctypes.c_char_p
        dll.parakeet_capi_free_string.argtypes = [ptr]
        dll.parakeet_capi_transcribe_pcm.argtypes = [
            ptr,
            ctypes.POINTER(ctypes.c_float),
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
        ]
        dll.parakeet_capi_transcribe_pcm.restype = ptr
        dll.parakeet_capi_vad_pcm_json.argtypes = [
            ptr,
            ctypes.POINTER(ctypes.c_float),
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_char_p,
        ]
        dll.parakeet_capi_vad_pcm_json.restype = ptr
        if dll.parakeet_capi_abi_version() != 10:
            raise RuntimeError("ABI Parakeet incompatible (10 attendu).")
        ctx = dll.parakeet_capi_load(model_path.encode("utf-8"))
        if not ctx:
            raise RuntimeError("Chargement du checkpoint Ultra impossible.")
        silence = np.zeros(16000, np.float32)
        out = dll.parakeet_capi_vad_pcm_json(
            ctx, silence.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), len(silence), 16000, b"{}"
        )
        if not out:
            raise RuntimeError("Le runtime ne peut pas vérifier le backend du modèle Ultra.")
        try:
            info = json.loads(ctypes.string_at(out).decode("utf-8"))
        finally:
            dll.parakeet_capi_free_string(out)
        actual = info["backend"]
        if backend.casefold() != actual.casefold():
            raise RuntimeError("Le backend demandé n’est pas actif. Repli silencieux refusé.")
        vocabulary = NativeRecognitionVocabulary(dll, ctx)
        vocabulary_status = vocabulary.configure(phrases)
        # Allocate encoder/decoder buffers before advertising readiness. The first
        # dictated segment then uses the same warm model as subsequent segments.
        warmup = vocabulary.transcribe(
            ctx, silence.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), len(silence), 16000, 0
        )
        if not warmup:
            raise RuntimeError("Le préchauffage du moteur Parakeet a échoué.")
        dll.parakeet_capi_free_string(warmup)
        connection.send({"ready": True, "backend": actual, "abi": 10, "vocabulary": vocabulary_status})
        transcribe = vocabulary.transcribe
        while True:
            audio = connection.recv()
            if audio is None:
                break
            if isinstance(audio, dict) and audio.get("kind") == "vocabulary":
                connection.send({"vocabulary": vocabulary.configure(audio["phrases"])})
                transcribe = vocabulary.transcribe
                continue
            audio = np.ascontiguousarray(audio, dtype=np.float32)
            out = transcribe(
                ctx, audio.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), len(audio), 16000, 0
            )
            if not out:
                connection.send({"error": "Inférence Parakeet interrompue."})
                continue
            try:
                text = ctypes.string_at(out).decode("utf-8")
            finally:
                dll.parakeet_capi_free_string(out)
            connection.send({"text": text})
    except BaseException as error:
        cause = error
        while cause.__cause__ is not None:
            cause = cause.__cause__
        winerror = getattr(cause, "winerror", None)
        try:
            connection.send(
                {
                    "error": str(error)
                    if isinstance(error, RuntimeError)
                    else f"Runtime Parakeet {backend} : {type(error).__name__}"
                    + (f" (Windows {winerror})" if winerror is not None else ""),
                    "winerror": winerror,
                }
            )
        except (OSError, EOFError):
            pass
    finally:
        try:
            if ctx:
                dll.parakeet_capi_free(ctx)
        finally:
            try:
                shutdown_backend(dll)
            finally:
                connection.close()
                dll_dirs.close()
