"""Search only the runtime folder, Windows, and explicit CUDA toolkit folders."""

import ctypes
import os
from contextlib import ExitStack, contextmanager
from pathlib import Path


def library_directories(binary):
    paths = [Path(binary).parent]
    for key, value in os.environ.items():
        if key == "CUDA_PATH" or key.startswith("CUDA_PATH_V12_"):
            path = Path(value) / "bin"
            if path.is_dir() and path not in paths:
                paths.append(path)
    return paths


def missing_cuda_libraries(binary):
    paths = library_directories(binary) + [Path(os.environ.get("SystemRoot", "C:/Windows")) / "System32"]
    return [
        name for name in ("cudart64_12.dll", "cublas64_12.dll", "cublasLt64_12.dll")
        if not any((folder / name).is_file() for folder in paths)
    ]


@contextmanager
def load_library(binary):
    with ExitStack() as stack:
        for folder in library_directories(binary):
            stack.enter_context(os.add_dll_directory(str(folder)))
        yield ctypes.CDLL(str(binary))


def shutdown_backend(library):
    shutdown = getattr(library, "transcrinator_shutdown_backend", None)
    if shutdown:
        shutdown.argtypes = []
        shutdown.restype = None
        shutdown()
