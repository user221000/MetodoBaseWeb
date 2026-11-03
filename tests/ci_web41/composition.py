"""Finite current41 source companion; see source-companions.json."""
from pathlib import Path as _Path
import sys as _sys
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from tests.ci_web41.source_companion import populate as _populate
_populate(globals(), __file__)

from tests.ci_web41.collection import install as _install
_install(globals())

from tests.ci_web41.google_mail_fixture_transition import specification as _mail_specification
from tests.ci_web41.google_mail_fixture_transition import source_photo as _mail_source_photo
from tests.ci_web41.google_mail_fixture_transition import require_quiet as _mail_require_quiet

_parent_specification = globals()["specification"]
_parent_sessionfinish = globals()["pytest_sessionfinish"]
_mail_initial_photo = None


def specification():
    global _mail_initial_photo
    result = _mail_specification(_parent_specification())
    if _mail_initial_photo is None:
        _mail_initial_photo = _mail_source_photo()
    else:
        _mail_require_quiet(_mail_initial_photo)
    return result


def pytest_sessionfinish(session, exitstatus):
    if _mail_initial_photo is not None:
        _mail_require_quiet(_mail_initial_photo)
    return _parent_sessionfinish(session, exitstatus)
