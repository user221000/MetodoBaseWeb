"""An outage or cached result never creates desktop license authority."""
import sqlite3
import urllib.error
from datetime import datetime

import pytest

from core.licencia import GestorLicencias


@pytest.fixture
def local_license(tmp_path, monkeypatch):
    monkeypatch.setattr(GestorLicencias, "ARCHIVO_CONFIG", str(tmp_path / "config.json"))
    monkeypatch.setattr(GestorLicencias, "ARCHIVO_LICENCIA", str(tmp_path / "license.json"))
    monkeypatch.setattr(GestorLicencias, "_CACHE_DB", str(tmp_path / "cache.sqlite"))
    gestor = GestorLicencias()
    gestor.SALT_MASTER = "synthetic-offline-license-test"

    def outage(*args, **kwargs):
        raise urllib.error.URLError("synthetic-network-unavailable")
    monkeypatch.setattr("urllib.request.urlopen", outage)
    return gestor


def issue(gestor):
    key = gestor.generar_key_activacion(gestor.obtener_id_instalacion(), 6)
    assert gestor.activar_licencia_con_key("Synthetic Gym", key, 6)[0]
    return key


def test_outage_does_not_validate_unknown_license(local_license):
    assert local_license.validar_licencia_online("PRO-not-issued-anywhere")[0] is False


def test_positive_cache_cannot_validate_unknown_license(local_license):
    with local_license._get_cache_conn() as db:
        db.execute("INSERT INTO cache_validacion (hardware_id, valida, mensaje, ts) VALUES (?, 1, 'synthetic-positive', ?)",
                   (local_license.obtener_id_instalacion(), datetime.now().timestamp()))
    assert local_license.validar_licencia_online("PRO-not-issued-anywhere")[0] is False


def test_valid_local_license_continues_offline_without_changing_expiry(local_license):
    key = issue(local_license)
    before = local_license.ruta_licencia.read_bytes()
    ok, message = local_license.validar_licencia_online(key)
    assert ok is True and "local" in message.lower()
    assert local_license.ruta_licencia.read_bytes() == before


def test_another_key_cannot_reuse_a_valid_local_license(local_license):
    issue(local_license)
    assert local_license.validar_licencia_online("PRO-not-issued-anywhere")[0] is False


def test_cache_failure_plus_network_failure_is_safe(local_license, monkeypatch):
    key = issue(local_license)
    def broken_cache():
        raise sqlite3.OperationalError("synthetic-cache-unavailable")
    monkeypatch.setattr(local_license, "_get_cache_conn", broken_cache)
    assert local_license.validar_licencia_online(key)[0] is True
