"""Original assertion and owner-boundary conservation; no SQL or fixture body."""
import ast
import hashlib
import json

import pytest

from tests.ci_web37 import fixtures, pg_onboarding, pg_originals


def test_original31_aliases_select_every_business_object_and_never_the_old_owner_witness():
    namespace = pg_originals.security31()
    assert len([name for name in namespace if name.startswith("test_")]) == 14
    assert namespace["followup_db"] is fixtures.followup_db
    assert namespace["current37_witness"] is fixtures.current37_witness
    assert "restricted_witness" not in namespace and "owned_database" not in namespace
    for name, value in namespace.items():
        if name.startswith("test_"):
            assert value.__name__ == name
            assert value.__code__.co_filename.endswith(".py.RAW")


@pytest.mark.parametrize("name,objects", [("test_security_qa26_primary_peer.py", 4),
                                         ("test_registration_bearer_ui27_canary.py", 1)])
def test_the_two_QA_modules_keep_original_test_code_and_use_only_the_current_fixture(name, objects):
    namespace = pg_originals.primary9(name)
    assert len([key for key in namespace if key.startswith("test_")]) == objects
    assert namespace["followup_db"] is fixtures.followup_db
    assert namespace["current37_witness"] is fixtures.current37_witness
    assert namespace["outbound_transport_is_synthetic"].__name__ == "outbound_transport_is_synthetic"


@pytest.mark.parametrize("name", list(pg_onboarding.PINS))
def test_R22_all_assertion_ASTs_survive_the_explicit_one_import_transport(name):
    raw = (pg_onboarding.ROOT / name).read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(raw).hexdigest() == pg_onboarding.PINS[name]
    source = raw.decode()
    revised = source.replace(pg_onboarding.OLD_IMPORT, pg_onboarding.NEW_IMPORT)
    old = [ast.dump(node, include_attributes=False) for node in ast.walk(ast.parse(source))
           if isinstance(node, ast.Assert)]
    new = [ast.dump(node, include_attributes=False) for node in ast.walk(ast.parse(revised))
           if isinstance(node, ast.Assert)]
    assert old == new and old
    namespace = pg_onboarding.export(name, "tests.current37_R22_control")
    assert namespace["Session"] is pg_onboarding.setup_session
    assert namespace["test_gym_user"] is pg_onboarding.onboarding_owner
    assert namespace["followup_db"] is fixtures.followup_db
    assert namespace["current37_witness"] is fixtures.current37_witness


def test_all_seven_executed_RAW_preimages_have_their_exact_recorded_hash_and_length():
    value = json.loads(pg_originals.SPEC.read_bytes())
    assert len(value["files"]) == 7
    for name, row in value["files"].items():
        raw, _path = pg_originals.raw(name)
        assert hashlib.sha256(raw).hexdigest() == row["raw_sha256"]
        assert len(raw) == row["bytes"]


def test_unowned_R22_setup_or_readonly_ports_cannot_choose_an_engine_or_subject():
    assert pg_onboarding.CASE.get() is None
    with pytest.raises(ValueError, match="actual restricted"):
        pg_onboarding.setup_session(object())
    with pytest.raises(ValueError, match="own persisted"), pg_onboarding.direct_readonly_session():
        pytest.fail("No session may be yielded without its owned persisted actor")
