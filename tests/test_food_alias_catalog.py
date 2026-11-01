"""All bundled canonical foods are recognized; historical aliases stay stable."""
from core.services.alimentos_alias import ALIAS_MAPA,NOMBRES_CANONICOS,es_canonico,resolver
from src.alimentos_seed_runtime import ALIMENTOS_BASE_SEED


def test_canonical_registry_matches_all_runtime_foods_without_ghosts():
    assert NOMBRES_CANONICOS==frozenset(ALIMENTOS_BASE_SEED)
    assert len(NOMBRES_CANONICOS)==171
    assert all(es_canonico(name) and resolver(name)==name for name in ALIMENTOS_BASE_SEED)


def test_historical_alias_targets_are_real_foods_without_changing_the_mapping():
    expected={'atun':'atun_en_agua','carne_molida':'carne_molida_res','pavo':'pavo_pechuga',
              'sardina':'sardinas','cerdo_lomo':'lomo_cerdo','tofu':'tofu_firme'}
    assert ALIAS_MAPA==expected
    assert all(resolver(alias)==target and target in NOMBRES_CANONICOS for alias,target in expected.items())
