"""
Tests de seguridad para AuthService y GestorUsuarios.

Verifican:
  1. Registro con hash bcrypt — la contraseña nunca se guarda en plano.
  2. Login exitoso con credenciales correctas.
  3. Login fallido con contraseña incorrecta.
  4. Respuesta genérica: no se puede distinguir email inválido de contraseña incorrecta.
  5. Doble registro con el mismo email es rechazado.
  6. Contraseña débil es rechazada en registro.
  7. Campos PII cifrados en DB — nunca aparecen en texto plano en el archivo SQLite.
  8. logout() limpia la sesión.
"""
from __future__ import annotations

import sqlite3

import pytest

from core.services.auth_service import AuthService, crear_auth_service
from core.services.crypto_service import CryptoService
from core.services.key_manager import KeyManager
from core.services.password_hasher import PasswordHasher
from src.gestor_usuarios import GestorUsuarios


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture()
def km(tmp_path):
    k = KeyManager(key_path=tmp_path / "keys.json")
    k.create_key()
    return k


@pytest.fixture()
def crypto(km):
    return CryptoService(km)


@pytest.fixture()
def gestor(tmp_path, crypto):
    return GestorUsuarios(db_path=str(tmp_path / "usuarios.db"), crypto_service=crypto)


@pytest.fixture()
def auth(gestor):
    return AuthService(gestor_usuarios=gestor)


_PW_FUERTE = "M3todo!Base2026"
_PW_DEBIL  = "abc123"


# ── Tests de registro ────────────────────────────────────────────────────────


def test_registro_exitoso(auth):
    res = auth.registrar("Ana", "García", "ana@gym.com", _PW_FUERTE)
    assert res.ok
    assert res.sesion is not None
    assert res.sesion.nombre_display == "Ana"


def test_contrasena_nunca_guardada_en_plano(auth, gestor, tmp_path):
    auth.registrar("Carlos", "López", "carlos@gym.com", _PW_FUERTE)
    # Leer el archivo SQLite directamente y verificar que la contraseña no aparece
    db_path = gestor._db_path
    raw = db_path.read_bytes()
    assert _PW_FUERTE.encode() not in raw, (
        "La contraseña en texto plano fue encontrada en el archivo de base de datos."
    )


def test_campos_pii_cifrados_en_db(auth, gestor):
    auth.registrar("Laura", "Martínez", "laura@gym.com", _PW_FUERTE)
    db_path = gestor._db_path
    raw = db_path.read_bytes()
    # Nombre y email no deben aparecer en texto plano
    for dato in (b"Laura", b"laura@gym.com", b"Mart"):
        assert dato not in raw, (
            f"Dato PII '{dato}' encontrado en texto plano en la base de datos."
        )


def test_contrasena_debil_rechazada(auth):
    res = auth.registrar("Pedro", "Ruiz", "pedro@gym.com", _PW_DEBIL)
    assert not res.ok
    assert res.errores


def test_doble_registro_mismo_email(auth):
    auth.registrar("Ana", "García", "dup@gym.com", _PW_FUERTE)
    res2 = auth.registrar("Otro", "Nombre", "dup@gym.com", _PW_FUERTE)
    assert not res2.ok


# ── Tests de login ───────────────────────────────────────────────────────────


def test_login_exitoso(auth):
    auth.registrar("Eva", "Torres", "eva@gym.com", _PW_FUERTE)
    auth.logout()
    res = auth.login("eva@gym.com", _PW_FUERTE)
    assert res.ok
    assert auth.autenticado
    assert auth.sesion_activa is not None


def test_login_contrasena_incorrecta(auth):
    auth.registrar("Luis", "Vera", "luis@gym.com", _PW_FUERTE)
    auth.logout()
    res = auth.login("luis@gym.com", "WrongPass99!")
    assert not res.ok


def test_login_email_inexistente_mensaje_generico(auth):
    res = auth.login("noexiste@gym.com", _PW_FUERTE)
    assert not res.ok
    # Mensaje genérico — no debe filtrar si el email existe
    assert "Email o contraseña incorrectos" in res.errores[0]


def test_login_respuesta_igual_email_invalido_y_pw_invalida(auth):
    auth.registrar("Sara", "Díaz", "sara@gym.com", _PW_FUERTE)
    auth.logout()
    res_pw_mal   = auth.login("sara@gym.com", "WrongPass99!")
    res_no_email = auth.login("noexiste@gym.com", _PW_FUERTE)
    # Ambos deben tener el mismo mensaje de error (sin filtrar si email existe)
    assert res_pw_mal.errores[0] == res_no_email.errores[0]


# ── Tests de logout y sesión ─────────────────────────────────────────────────


def test_logout_limpia_sesion(auth):
    auth.registrar("Mia", "Flores", "mia@gym.com", _PW_FUERTE)
    assert auth.autenticado
    auth.logout()
    assert not auth.autenticado
    assert auth.sesion_activa is None


def test_sesion_no_expone_password_hash(auth):
    auth.registrar("Tom", "Ríos", "tom@gym.com", _PW_FUERTE)
    sesion = auth.sesion_activa
    # SesionActiva solo tiene id_usuario, nombre_display, rol
    assert not hasattr(sesion, "password_hash")
    assert not hasattr(sesion, "email")


# ── Tests de filtrado de exportación ─────────────────────────────────────────


def test_export_filter_no_incluye_hash_ni_email():
    from core.exportador_multi import filtrar_campos_cliente_export
    cliente = {
        "nombre": "Test",
        "edad": 25,
        "peso_kg": 70,
        "estatura_cm": 175,
        "grasa_corporal_pct": 18,
        "objetivo": "deficit",
        "nivel_actividad": "moderada",
        "email": "test@privado.com",
        "password_hash": "$2b$12$...",
        "nombre_enc": "v1:k_abc:token...",
        "email_enc": "v1:k_abc:token2...",
    }
    filtrado = filtrar_campos_cliente_export(cliente)
    for campo_sensible in ("email", "password_hash", "nombre_enc", "email_enc"):
        assert campo_sensible not in filtrado, (
            f"Campo sensible '{campo_sensible}' aparece en datos exportados."
        )
    assert filtrado["nombre"] == "Test"
