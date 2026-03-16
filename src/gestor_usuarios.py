"""
Gestor de cuentas de usuario del sistema (GestorUsuarios).

Tabla ``usuarios``:
  - id_usuario TEXT PRIMARY KEY (UUID v4)
  - nombre_enc TEXT            — nombre cifrado con CryptoService
  - apellido_enc TEXT          — apellido cifrado
  - email_enc TEXT             — email cifrado
  - email_idx TEXT             — HMAC-SHA256 del email normalizado (para búsqueda exacta)
  - password_hash TEXT         — bcrypt hash, NUNCA texto plano
  - rol TEXT                   — 'admin' | 'usuario' | 'gym'
  - activo BOOLEAN DEFAULT 1
  - fecha_registro TIMESTAMP
  - ultimo_acceso TIMESTAMP

Reglas de seguridad:
  - Ningún campo PII se escribe en texto plano en la BD.
  - El email_idx permite búsqueda exacta sin descifrar todos los registros.
  - Los logs nunca incluyen nombre, email ni password_hash.
"""
from __future__ import annotations

import hashlib
import hmac
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from config.constantes import CARPETA_REGISTROS
from utils.logger import logger

_ROLES_VALIDOS = {"admin", "usuario", "gym"}
_HMAC_EMAIL_SALT = b"metodobase_email_idx_v1"  # fijo; no es secreto, es un namespace


class RegistroUsuario:
    """DTO inmutable para creación de un usuario."""

    __slots__ = ("id_usuario", "nombre", "apellido", "email", "password_hash", "rol")

    def __init__(
        self,
        nombre: str,
        apellido: str,
        email: str,
        password_hash: str,
        rol: str = "usuario",
        id_usuario: str | None = None,
    ) -> None:
        if rol not in _ROLES_VALIDOS:
            raise ValueError(f"Rol inválido: {rol!r}. Válidos: {_ROLES_VALIDOS}")
        self.id_usuario = id_usuario or str(uuid.uuid4())
        self.nombre = nombre.strip()
        self.apellido = apellido.strip()
        self.email = email.strip().lower()
        self.password_hash = password_hash
        self.rol = rol


class GestorUsuarios:
    """
    Administra cuentas de usuario con almacenamiento cifrado.

    Requiere un ``CryptoService`` activo para leer/escribir campos PII.
    """

    def __init__(
        self,
        db_path: str | None = None,
        crypto_service=None,
    ) -> None:
        if db_path is None:
            db_path = str(Path(CARPETA_REGISTROS) / "usuarios.db")
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._crypto = crypto_service
        self._crear_tablas()
        logger.info("[USUARIOS] GestorUsuarios inicializado")

    # ------------------------------------------------------------------
    # Esquema
    # ------------------------------------------------------------------

    def _crear_tablas(self) -> None:
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id_usuario    TEXT PRIMARY KEY,
                    nombre_enc    TEXT NOT NULL,
                    apellido_enc  TEXT NOT NULL,
                    email_enc     TEXT NOT NULL,
                    email_idx     TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    rol           TEXT NOT NULL DEFAULT 'usuario'
                                  CHECK(rol IN ('admin','usuario','gym')),
                    activo        INTEGER NOT NULL DEFAULT 1,
                    fecha_registro TEXT NOT NULL,
                    ultimo_acceso  TEXT
                )
            """)
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_email_idx ON usuarios(email_idx)"
            )
            conn.commit()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        # Habilitar WAL para mayor concurrencia
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    @staticmethod
    def _email_idx(email: str) -> str:
        """HMAC-SHA256 del email normalizado para búsqueda sin descifrar."""
        return hmac.new(
            _HMAC_EMAIL_SALT,
            email.strip().lower().encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _cifrar(self, valor: str) -> str:
        if self._crypto is None:
            raise RuntimeError("CryptoService no configurado; no se pueden cifrar datos.")
        return self._crypto.encrypt(valor)

    def _descifrar(self, valor: str) -> str:
        if self._crypto is None:
            raise RuntimeError("CryptoService no configurado; no se pueden descifrar datos.")
        if not valor:
            return ""
        return self._crypto.decrypt(valor)

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def crear_usuario(self, registro: RegistroUsuario) -> None:
        """
        Inserta un nuevo usuario con campos PII cifrados.

        Raises:
            ValueError: si el email ya existe.
            RuntimeError: si CryptoService no está configurado.
        """
        email_idx = self._email_idx(registro.email)

        with self._conn() as conn:
            # Verificar unicidad de email sin descifrar registros
            existe = conn.execute(
                "SELECT 1 FROM usuarios WHERE email_idx = ?", (email_idx,)
            ).fetchone()
            if existe:
                raise ValueError("Ya existe una cuenta con ese email.")

            conn.execute(
                """
                INSERT INTO usuarios
                    (id_usuario, nombre_enc, apellido_enc, email_enc, email_idx,
                     password_hash, rol, activo, fecha_registro, ultimo_acceso)
                VALUES (?,?,?,?,?,?,?,1,?,NULL)
                """,
                (
                    registro.id_usuario,
                    self._cifrar(registro.nombre),
                    self._cifrar(registro.apellido),
                    self._cifrar(registro.email),
                    email_idx,
                    registro.password_hash,
                    registro.rol,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.commit()
        logger.info("[USUARIOS] Usuario creado id=***")

    def obtener_por_email(self, email: str) -> Optional[dict]:
        """
        Busca usuario por email (usando índice HMAC); descifra campos PII.

        Returns:
            dict con claves id_usuario, nombre, apellido, email, password_hash,
            rol, activo, fecha_registro, ultimo_acceso — o None si no existe.
        """
        email_idx = self._email_idx(email)
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM usuarios WHERE email_idx = ? AND activo = 1",
                (email_idx,),
            ).fetchone()
        if not row:
            return None
        return self._desencriptar_fila(dict(row))

    def obtener_por_id(self, id_usuario: str) -> Optional[dict]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM usuarios WHERE id_usuario = ? AND activo = 1",
                (id_usuario,),
            ).fetchone()
        if not row:
            return None
        return self._desencriptar_fila(dict(row))

    def obtener_hash_por_email(self, email: str) -> Optional[str]:
        """Retorna solo el password_hash (sin descifrar PII), para verificación."""
        email_idx = self._email_idx(email)
        with self._conn() as conn:
            row = conn.execute(
                "SELECT password_hash FROM usuarios WHERE email_idx = ? AND activo = 1",
                (email_idx,),
            ).fetchone()
        return row["password_hash"] if row else None

    def actualizar_ultimo_acceso(self, id_usuario: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE usuarios SET ultimo_acceso = ? WHERE id_usuario = ?",
                (datetime.now(timezone.utc).isoformat(), id_usuario),
            )
            conn.commit()

    def desactivar_usuario(self, id_usuario: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE usuarios SET activo = 0 WHERE id_usuario = ?",
                (id_usuario,),
            )
            conn.commit()
        logger.info("[USUARIOS] Usuario desactivado id=***")

    def total_usuarios(self) -> int:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM usuarios WHERE activo = 1"
            ).fetchone()
        return row[0] if row else 0

    def existe_cuenta_gym(self) -> bool:
        """Devuelve True si hay al menos una cuenta con rol='gym' activa."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM usuarios WHERE rol = 'gym' AND activo = 1 LIMIT 1"
            ).fetchone()
        return row is not None

    def listar_por_rol(self, rol: str) -> list[dict]:
        """Devuelve lista de usuarios con el rol dado (campos PII descifrados)."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM usuarios WHERE rol = ? AND activo = 1", (rol,)
            ).fetchall()
        return [self._desencriptar_fila(dict(r)) for r in rows]

    # ------------------------------------------------------------------
    # Privado: descifrar fila completa
    # ------------------------------------------------------------------

    def _desencriptar_fila(self, row: dict) -> dict:
        return {
            "id_usuario":     row["id_usuario"],
            "nombre":         self._descifrar(row.get("nombre_enc", "")),
            "apellido":       self._descifrar(row.get("apellido_enc", "")),
            "email":          self._descifrar(row.get("email_enc", "")),
            "password_hash":  row["password_hash"],
            "rol":            row["rol"],
            "activo":         bool(row["activo"]),
            "fecha_registro": row.get("fecha_registro", ""),
            "ultimo_acceso":  row.get("ultimo_acceso", ""),
        }
