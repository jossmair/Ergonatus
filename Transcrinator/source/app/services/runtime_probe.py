"""Check native ABI in an expendable process; do not load model weights."""

import sys

from app.engines.native_library import load_library


def probe(binary):
    try:
        with load_library(binary) as library:
            return 0 if library.parakeet_capi_abi_version() == 10 else 1
    except (OSError, AttributeError):
        return 1


if __name__ == "__main__":
    sys.exit(probe(sys.argv[1]))
