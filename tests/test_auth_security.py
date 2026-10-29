"""
tests/test_auth_security.py — Tests que validan seguridad de autenticación.

Verifica:
1. bcrypt es OBLIGATORIO (no hay fallback)
2. Hash SHA256 legacy NO es aceptado
3. Contraseñas nunca se guardan en plano
4. Timing attacks mitigados
"""
import pytest
import time


class TestBcryptRequired:
    """Tests que verifican que bcrypt es obligatorio."""
    
    def test_bcrypt_is_available(self):
        """bcrypt debe estar disponible en el sistema."""
        from web.auth import _BCRYPT_AVAILABLE
        
        assert _BCRYPT_AVAILABLE is True, (
            "bcrypt no está disponible. Instala con: pip install bcrypt"
        )
    
    def test_hash_password_works(self):
        """hash_password debe funcionar con bcrypt."""
        from web.auth import hash_password
        
        hashed = hash_password("test_password_123")
        
        # bcrypt hashes empiezan con $2b$ o $2a$
        assert hashed.startswith("$2"), f"Hash no parece bcrypt: {hashed[:20]}"
    
    def test_verify_password_works(self):
        """verify_password debe validar correctamente."""
        from web.auth import hash_password, verify_password
        
        password = "my_secure_password_456"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True
        assert verify_password("wrong_password", hashed) is False


class TestNoSHA256Fallback:
    """Tests que verifican que SHA256 NO es aceptado."""
    
    def test_sha256_hash_not_verified(self):
        """Hashes SHA256 legacy NO deben ser verificados."""
        from web.auth import verify_password
        import hashlib
        import os
        
        # Crear un hash SHA256 como lo hacía el código legacy
        password = "test_password"
        salt = os.urandom(16).hex()
        sha256_hash = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
        legacy_hash = f"sha256${salt}${sha256_hash}"
        
        # Este hash NO debe ser verificado por verify_password
        # porque bcrypt.checkpw rechazará el formato
        result = verify_password(password, legacy_hash)
        
        assert result is False, (
            "¡SECURITY ISSUE! Hash SHA256 legacy fue aceptado. "
            "El fallback inseguro sigue activo."
        )
    
    def test_only_bcrypt_format_accepted(self):
        """Solo hashes con formato bcrypt deben ser aceptados."""
        from web.auth import hash_password, verify_password
        
        password = "test_password"
        bcrypt_hash = hash_password(password)
        
        # Verificar que es formato bcrypt ($2b$ o $2a$)
        assert bcrypt_hash.startswith("$2"), "Hash no es formato bcrypt"
        
        # Verificar que funciona
        assert verify_password(password, bcrypt_hash) is True


class TestPasswordNeverPlain:
    """Tests que verifican que contraseñas nunca están en plano."""
    
    def test_hash_is_different_from_password(self):
        """El hash debe ser diferente de la contraseña."""
        from web.auth import hash_password
        
        password = "my_password_123"
        hashed = hash_password(password)
        
        assert hashed != password
        assert password not in hashed
    
    def test_same_password_different_hash(self):
        """El mismo password debe producir hashes diferentes (salt)."""
        from web.auth import hash_password
        
        password = "repeated_password"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        assert hash1 != hash2, "Hashes idénticos indican falta de salt aleatorio"


class TestTimingAttackMitigation:
    """Tests básicos de mitigación de timing attacks."""
    
    def test_wrong_password_similar_time(self):
        """Verificación de password incorrecto no debe ser instantánea."""
        from web.auth import hash_password, verify_password
        
        password = "correct_password"
        hashed = hash_password(password)
        
        # Medir tiempo de verificación correcta
        start = time.perf_counter()
        verify_password(password, hashed)
        correct_time = time.perf_counter() - start
        
        # Medir tiempo de verificación incorrecta
        start = time.perf_counter()
        verify_password("wrong_password", hashed)
        wrong_time = time.perf_counter() - start
        
        # Ambos tiempos deben ser similares (bcrypt es constante)
        # Permitimos hasta 5x diferencia debido a variabilidad del sistema
        ratio = max(correct_time, wrong_time) / max(min(correct_time, wrong_time), 0.0001)
        
        assert ratio < 5, (
            f"Timing difference suspicious: correct={correct_time:.4f}s, "
            f"wrong={wrong_time:.4f}s, ratio={ratio:.2f}x"
        )


class TestRegistroUsuario:
    """Tests de registro de usuario con hash seguro."""
    
    def test_registro_usa_bcrypt(self):
        """El registro debe usar bcrypt para el hash."""
        from web.auth import init_auth, crear_usuario
        from web.database.engine import get_engine
        from web.database.models import Usuario
        from sqlalchemy.orm import Session as SASession
        import os
        
        init_auth()
        
        # Registrar usuario de test
        test_email = f"test_bcrypt_{os.urandom(4).hex()}@test.com"
        try:
            result = crear_usuario(
                email=test_email,
                password="Synthet1c Bcrypt 37!",
                nombre="Test",
                apellido="User",
                tipo="gym"
            )
            
            # Verificar que el hash en BD es bcrypt
            engine = get_engine()
            with SASession(engine) as session:
                row = session.query(Usuario).filter(Usuario.email == test_email).first()
            
            assert row is not None, "Usuario no fue guardado"
            assert row.password_hash.startswith("$2"), (
                f"Hash en BD no es bcrypt: {row.password_hash[:20]}"
            )
            
        finally:
            # Limpiar usuario de test
            try:
                engine = get_engine()
                with SASession(engine) as session:
                    session.query(Usuario).filter(Usuario.email == test_email).delete()
                    session.commit()
            except Exception:
                pass
