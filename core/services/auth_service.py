"""
AuthService — Autenticación segura de usuarios.

Responsabilidades:
  - Registro con hash bcrypt + cifrado de campos PII.
  - Login con verificación de hash; nunca expone password_hash a la UI.
  - Gestión de sesión en memoria (sin tokens persistentes en disco por defecto).
  - Rehash transparente si la política de hash cambió.

Reglas de seguridad aplicadas:
  - La UI solo recibe id_usuario, nombre_display y rol.
  - El password_hash nunca se propaga fuera de este módulo ni del GestorUsuarios.
  - Los logs nunca incluyen nombre, email ni contraseñas.
  - Un intento fallido NO indica si el email existe (misma respuesta genérica).
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import Optional

from core.services.password_hasher import PasswordHasher, PasswordPolicy
from src.gestor_usuarios import GestorUsuarios, RegistroUsuario
from utils.logger import logger


# ---------------------------------------------------------------------------
# DTO sesión — lo único que la UI recibe tras autenticarse
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SesionActiva:
    """Datos no sensibles disponibles para la UI tras autenticación exitosa."""
    id_usuario: str
    nombre_display: str   # solo nombre, sin apellido
    rol: str


# ---------------------------------------------------------------------------
# Resultado de operación de autenticación
# ---------------------------------------------------------------------------

@dataclass
class ResultadoAuth:
    ok: bool
    sesion: Optional[SesionActiva] = None
    errores: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Servicio
# ---------------------------------------------------------------------------

class AuthService:
    """
    Capa de autenticación entre la UI y la base de datos de usuarios.

    >>> auth = AuthService(gestor_usuarios=..., password_hasher=...)
    >>> resultado = auth.registrar("Ana", "García", "ana@gym.com", "P@ss4Gym!")
    >>> resultado = auth.login("ana@gym.com", "P@ss4Gym!")
    >>> auth.sesion_activa  # SesionActiva(id_usuario=..., ...)
    """

    # Regex de email mínimo (no RFC compliant intencionalmente; sencillo)
    _RE_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    _MAX_NOMBRE_LEN = 80
    _MAX_EMAIL_LEN = 254     # RFC 5321

    def __init__(
        self,
        gestor_usuarios: GestorUsuarios,
        password_hasher: PasswordHasher | None = None,
    ) -> None:
        self._gu = gestor_usuarios
        self._ph = password_hasher or PasswordHasher()
        self._sesion: Optional[SesionActiva] = None

    # ------------------------------------------------------------------
    # Propiedades de sesión (solo lectura)
    # ------------------------------------------------------------------

    @property
    def autenticado(self) -> bool:
        return self._sesion is not None

    @property
    def sesion_activa(self) -> Optional[SesionActiva]:
        """Retorna la sesión activa o None. La UI nunca modifica este objeto."""
        return self._sesion

    # ------------------------------------------------------------------
    # Registro
    # ------------------------------------------------------------------

    def registrar(
        self,
        nombre: str,
        apellido: str,
        email: str,
        password: str,
        rol: str = "usuario",
    ) -> ResultadoAuth:
        """
        Registra un nuevo usuario.

        El ``password`` se hashea antes de persistir; nunca se almacena en plano.

        Returns:
            ResultadoAuth con ok=True y sesion, o ok=False con lista de errores.
        """
        errores = self._validar_registro(nombre, apellido, email, password)
        if errores:
            return ResultadoAuth(ok=False, errores=errores)

        try:
            hash_pw = self._ph.hash_password(password)
        except ValueError as exc:
            return ResultadoAuth(ok=False, errores=[str(exc)])

        try:
            registro = RegistroUsuario(
                nombre=nombre.strip(),
                apellido=apellido.strip(),
                email=email.strip().lower(),
                password_hash=hash_pw,
                rol=rol,
            )
            self._gu.crear_usuario(registro)
        except ValueError as exc:
            # Ej: email duplicado — no revelar si el email existe externamente
            logger.warning("[AUTH] Registro rechazado (sin detalles por seguridad)")
            return ResultadoAuth(ok=False, errores=["No se pudo completar el registro."])
        except Exception as exc:
            logger.error("[AUTH] Error inesperado en registro")
            return ResultadoAuth(ok=False, errores=["Error interno; intente más tarde."])

        sesion = SesionActiva(
            id_usuario=registro.id_usuario,
            nombre_display=nombre.strip().split()[0],
            rol=rol,
        )
        self._sesion = sesion
        logger.info("[AUTH] Nuevo usuario registrado id=*** rol=%s", rol)
        return ResultadoAuth(ok=True, sesion=sesion)

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------

    def login(self, email: str, password: str) -> ResultadoAuth:
        """
        Autentica con email + contraseña.

        La respuesta de error es genérica para no filtrar si el email existe.

        Returns:
            ResultadoAuth con sesion activa si credenciales son correctas.
        """
        _MSG_ERROR = "Email o contraseña incorrectos."

        if not email or not password:
            return ResultadoAuth(ok=False, errores=[_MSG_ERROR])

        email_norm = email.strip().lower()

        # Obtener hash sin descifrar PII
        hash_almacenado = self._gu.obtener_hash_por_email(email_norm)
        if hash_almacenado is None:
            # Ejecutar verificación "dummy" para prevenir timing attack
            # (usa un hash pre-computado; no llama a hash_password para evitar
            #  que la validación de política revele si el email existe)
            _DUMMY_HASH = (
                "$2b$12$duMMYhAshValUEfOrTimiNgATtAcKpreVentionXXXXXXXXXXXXXXXX"
            )
            try:
                self._ph.verify_password(password, _DUMMY_HASH)
            except Exception:
                pass
            return ResultadoAuth(ok=False, errores=[_MSG_ERROR])

        try:
            valido = self._ph.verify_password(password, hash_almacenado)
        except Exception:
            valido = False

        if not valido:
            return ResultadoAuth(ok=False, errores=[_MSG_ERROR])

        # Rehash si política actualizó número de rounds
        if self._ph.needs_update(hash_almacenado):
            self._actualizar_hash(email_norm, password)

        usuario = self._gu.obtener_por_email(email_norm)
        if not usuario:
            return ResultadoAuth(ok=False, errores=[_MSG_ERROR])

        self._gu.actualizar_ultimo_acceso(usuario["id_usuario"])

        sesion = SesionActiva(
            id_usuario=usuario["id_usuario"],
            nombre_display=usuario["nombre"].split()[0] if usuario["nombre"] else "",
            rol=usuario["rol"],
        )
        self._sesion = sesion
        logger.info("[AUTH] Login exitoso rol=%s", sesion.rol)
        return ResultadoAuth(ok=True, sesion=sesion)

    # ------------------------------------------------------------------
    # Logout
    # ------------------------------------------------------------------

    def logout(self) -> None:
        self._sesion = None
        logger.info("[AUTH] Sesión cerrada")

    # ------------------------------------------------------------------
    # Helpers privados
    # ------------------------------------------------------------------

    def _validar_registro(
        self, nombre: str, apellido: str, email: str, password: str
    ) -> list[str]:
        errores: list[str] = []

        nombre = nombre.strip()
        apellido = apellido.strip()
        email = email.strip()

        if not nombre:
            errores.append("El nombre es obligatorio.")
        elif len(nombre) > self._MAX_NOMBRE_LEN:
            errores.append(f"Nombre demasiado largo (máx {self._MAX_NOMBRE_LEN} caracteres).")

        if not apellido:
            errores.append("El apellido es obligatorio.")
        elif len(apellido) > self._MAX_NOMBRE_LEN:
            errores.append(f"Apellido demasiado largo (máx {self._MAX_NOMBRE_LEN} caracteres).")

        if not email:
            errores.append("El email es obligatorio.")
        elif len(email) > self._MAX_EMAIL_LEN:
            errores.append("Email demasiado largo.")
        elif not self._RE_EMAIL.match(email):
            errores.append("El email no tiene formato válido.")

        if not password:
            errores.append("La contraseña es obligatoria.")
        else:
            try:
                self._ph._validate_strength(password)
            except ValueError as exc:
                errores.append(str(exc))

        return errores

    def _actualizar_hash(self, email: str, password: str) -> None:
        """Rehash silencioso si la política cambió."""
        try:
            nuevo_hash = self._ph.hash_password(password)
            usuario = self._gu.obtener_por_email(email)
            if usuario:
                with self._gu._conn() as conn:
                    conn.execute(
                        "UPDATE usuarios SET password_hash = ? WHERE id_usuario = ?",
                        (nuevo_hash, usuario["id_usuario"]),
                    )
                    conn.commit()
            logger.info("[AUTH] Hash actualizado por política nueva id=***")
        except Exception:
            logger.warning("[AUTH] No se pudo actualizar hash")


# ---------------------------------------------------------------------------
# Función de fábrica conveniente
# ---------------------------------------------------------------------------

def crear_auth_service(crypto_service=None) -> AuthService:
    """
    Crea un AuthService completamente configurado.

    Si ``crypto_service`` es None, intenta cargar uno desde KeyManager
    con la configuración por defecto.
    """
    if crypto_service is None:
        from core.services.key_manager import KeyManager
        from core.services.crypto_service import CryptoService
        km = KeyManager()
        if not km._key_path.exists():
            km.create_key()
        crypto_service = CryptoService(km)

    gestor = GestorUsuarios(crypto_service=crypto_service)
    return AuthService(gestor_usuarios=gestor)
