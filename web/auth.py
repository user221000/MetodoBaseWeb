"""
web/auth.py — Sistema de autenticación para MetodoBase Web

- Usuarios almacenados en SQLite local (sin cifrado, orientado a localhost)
- Contraseñas con bcrypt (passlib)
- Tokens: HMAC-SHA256 firmados (sin dependencias externas)
- Roles: 'gym' | 'usuario' | 'admin'
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Optional

try:
    import bcrypt as _bcrypt_lib
    def _hash_pw(pw: str) -> str:
        return _bcrypt_lib.hashpw(pw.encode("utf-8"), _bcrypt_lib.gensalt()).decode("utf-8")
    def _verify_pw(pw: str, hashed: str) -> bool:
        try:
            return _bcrypt_lib.checkpw(pw.encode("utf-8"), hashed.encode("utf-8"))
        except Exception:
            return False
except ImportError:
    try:
        from passlib.hash import bcrypt as _pl_bcrypt
        def _hash_pw(pw: str) -> str:
            return _pl_bcrypt.hash(pw)
        def _verify_pw(pw: str, hashed: str) -> bool:
            return _pl_bcrypt.verify(pw, hashed)
    except Exception:
        import hashlib as _hl
        # Fallback sin bcrypt — solo para entornos sin dependencias
        def _hash_pw(pw: str) -> str:
            salt = os.urandom(16).hex()
            h = _hl.sha256(f"{salt}{pw}".encode()).hexdigest()
            return f"sha256${salt}${h}"
        def _verify_pw(pw: str, hashed: str) -> bool:
            if hashed.startswith("sha256$"):
                _, salt, h = hashed.split("$")
                return _hl.sha256(f"{salt}{pw}".encode()).hexdigest() == h
            return False

# ── Configuración ──────────────────────────────────────────────────────────

SECRET_KEY = os.getenv(
    "WEB_SECRET_KEY",
    "metodobase_dev_secret_2026_CHANGE_IN_PROD"
)
TOKEN_EXPIRE_HOURS = int(os.getenv("WEB_TOKEN_EXPIRE_HOURS", "24"))


def _get_db_path() -> Path:
    try:
        from config.constantes import CARPETA_REGISTROS
        return Path(CARPETA_REGISTROS) / "web_usuarios.db"
    except Exception:
        return Path.home() / ".local" / "share" / "MetodoBase" / "web_usuarios.db"


def _conn() -> sqlite3.Connection:
    db = _get_db_path()
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ── Esquema ────────────────────────────────────────────────────────────────

def _crear_tablas() -> None:
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS web_usuarios (
                id             TEXT PRIMARY KEY,
                email          TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash  TEXT NOT NULL,
                nombre         TEXT NOT NULL,
                apellido       TEXT NOT NULL DEFAULT '',
                tipo           TEXT NOT NULL DEFAULT 'usuario'
                               CHECK(tipo IN ('gym','usuario','admin')),
                activo         INTEGER NOT NULL DEFAULT 1,
                fecha_registro TEXT NOT NULL
            )
        """)
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_wb_email ON web_usuarios(email)"
        )
        conn.commit()


def _seed_demo_users() -> None:
    """Crea usuarios demo si la tabla está vacía."""
    with _conn() as conn:
        count = conn.execute("SELECT COUNT(*) FROM web_usuarios").fetchone()[0]
        if count == 0:
            now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            demos = [
                (str(uuid.uuid4()), "gym@test.com",     _hash_pw("test123"), "Mi Gimnasio", "", "gym",     now),
                (str(uuid.uuid4()), "usuario@test.com", _hash_pw("test123"), "Juan",        "Pérez", "usuario", now),
            ]
            conn.executemany(
                "INSERT INTO web_usuarios(id,email,password_hash,nombre,apellido,tipo,fecha_registro) VALUES(?,?,?,?,?,?,?)",
                demos,
            )
            conn.commit()


# ── API pública ────────────────────────────────────────────────────────────

def init_auth() -> None:
    """Inicializa BD de autenticación y siembra usuarios demo."""
    _crear_tablas()
    _seed_demo_users()


def crear_usuario(
    email: str,
    password: str,
    nombre: str,
    apellido: str = "",
    tipo: str = "usuario",
) -> dict:
    """
    Registra un nuevo usuario.

    Raises:
        ValueError: si el email ya está registrado o el tipo es inválido.
    """
    tipos_validos = {"gym", "usuario"}
    if tipo not in tipos_validos:
        raise ValueError(f"Tipo inválido: {tipo!r}")

    email = email.strip().lower()
    if not email or "@" not in email:
        raise ValueError("Email inválido.")
    if len(password) < 6:
        raise ValueError("La contraseña debe tener al menos 6 caracteres.")

    with _conn() as conn:
        existe = conn.execute(
            "SELECT 1 FROM web_usuarios WHERE email=?", (email,)
        ).fetchone()
        if existe:
            raise ValueError("El email ya está registrado.")

        uid = str(uuid.uuid4())
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        conn.execute(
            "INSERT INTO web_usuarios(id,email,password_hash,nombre,apellido,tipo,fecha_registro) "
            "VALUES(?,?,?,?,?,?,?)",
            (uid, email, _hash_pw(password), nombre.strip(), apellido.strip(), tipo, now),
        )
        conn.commit()

    return {"id": uid, "email": email, "nombre": nombre.strip(), "tipo": tipo}


def verificar_credenciales(
    email: str,
    password: str,
    tipo_requerido: Optional[str] = None,
) -> Optional[dict]:
    """
    Verifica email + password.

    Args:
        tipo_requerido: si se indica, el usuario debe tener ese tipo (o 'admin').

    Returns:
        dict con datos del usuario, o None si las credenciales son inválidas.
    """
    email = email.strip().lower()
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM web_usuarios WHERE email=? AND activo=1", (email,)
        ).fetchone()

    if not row:
        return None

    # Verificación constante en tiempo para mitigar timing attacks
    if not _verify_pw(password, row["password_hash"]):
        return None

    if tipo_requerido and row["tipo"] not in (tipo_requerido, "admin"):
        return None

    return {
        "id":       row["id"],
        "email":    row["email"],
        "nombre":   row["nombre"],
        "apellido": row["apellido"],
        "tipo":     row["tipo"],
    }


# ── Tokens HMAC ────────────────────────────────────────────────────────────

def _sign(payload_b64: str) -> str:
    return hmac.new(
        SECRET_KEY.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def crear_token(usuario: dict, horas: Optional[int] = None) -> str:
    """Genera token HMAC-SHA256: base64(payload).signature"""
    exp = time.time() + (horas or TOKEN_EXPIRE_HOURS) * 3600
    payload = {
        "id":     usuario["id"],
        "email":  usuario["email"],
        "nombre": usuario["nombre"],
        "tipo":   usuario["tipo"],
        "exp":    exp,
    }
    payload_b64 = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":")).encode()
    ).decode().rstrip("=")
    sig = _sign(payload_b64)
    return f"{payload_b64}.{sig}"


def verificar_token(token: str) -> Optional[dict]:
    """
    Verifica y decodifica token firmado.

    Returns:
        dict con payload (id, email, nombre, tipo, exp) o None si inválido/expirado.
    """
    if not token:
        return None
    try:
        parts = token.rsplit(".", 1)
        if len(parts) != 2:
            return None
        payload_b64, sig = parts
        expected = _sign(payload_b64)
        # Comparación en tiempo constante
        if not hmac.compare_digest(sig, expected):
            return None
        # Restaurar padding base64
        padded = payload_b64 + "=" * (4 - len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded))
        if payload.get("exp", 0) < time.time():
            return None  # Expirado
        return payload
    except Exception:
        return None
