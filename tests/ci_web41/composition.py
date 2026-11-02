"""Finite current41 source companion; see source-companions.json."""
from pathlib import Path as _Path
import sys as _sys
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from tests.ci_web41.source_companion import populate as _populate
_populate(globals(), __file__)

from tests.ci_web41.collection import install as _install
_install(globals())
