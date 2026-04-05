"""Load the local sibling `../chroma/chromadb` package without building it."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


_REAL_PACKAGE_DIR = (
    Path(__file__).resolve().parent.parent.parent / "chroma" / "chromadb"
)
_REAL_INIT = _REAL_PACKAGE_DIR / "__init__.py"

if not _REAL_INIT.exists():
    msg = f"Expected local Chroma package at {_REAL_INIT}"
    raise ModuleNotFoundError(msg)

_SPEC = importlib.util.spec_from_file_location(
    __name__,
    _REAL_INIT,
    submodule_search_locations=[str(_REAL_PACKAGE_DIR)],
)

if _SPEC is None or _SPEC.loader is None:
    msg = f"Could not create import spec for {_REAL_INIT}"
    raise ImportError(msg)

_MODULE = sys.modules[__name__]
_MODULE.__file__ = str(_REAL_INIT)
_MODULE.__path__ = [str(_REAL_PACKAGE_DIR)]
_MODULE.__spec__ = _SPEC

_SPEC.loader.exec_module(_MODULE)
