# Seguridad y Privacidad — Método Base 2026

> **Audiencia:** Desarrolladores, integradores, auditores y responsables técnicos del sistema.

---

## 1. Resumen Ejecutivo

Método Base implementa un modelo de **defensa en profundidad** para proteger los datos personales (PII) de usuarios y clientes en cada capa del sistema: base de datos, servicios, UI y exportaciones. La arquitectura sigue los principios de **separación de responsabilidades**, **zero-trust hacia la UI** y **mínima exposición de datos sensibles**.

---

## 2. Arquitectura de Seguridad por Capas

```
┌─────────────────────────────────────────────────────────────────┐
│  UI (PySide6) — Solo recibe DTO no-sensibles (SesionActiva)     │
│  Nunca manipula hashes, tokens cifrados ni claves.              │
├─────────────────────────────────────────────────────────────────┤
│  Services / Core — AuthService, ClienteService, CryptoService   │
│  Única capa que hashea, cifra y descifra.                       │
├─────────────────────────────────────────────────────────────────┤
│  DB Layer — GestorUsuarios, GestorBDClientes                    │
│  Solo escribe datos cifrados/hasheados. Índices HMAC para       │
│  búsqueda sin descifrado masivo.                                │
├─────────────────────────────────────────────────────────────────┤
│  SQLite en disco — Solo datos cifrados (nombre_enc, email_enc)  │
│  y hashes bcrypt. Nunca PII en texto plano.                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Seguridad de Contraseñas

### Algoritmo
- **bcrypt** con número de rounds configurable (defecto: `12`).
- Librería: `bcrypt >= 4.x` usado **directamente** (no passlib, que no es compatible con bcrypt 4.x).
- Salt generado automáticamente por bcrypt; cada hash es único incluso para contraseñas idénticas.

### Política de contraseñas (`PasswordPolicy`)
| Requisito         | Por defecto |
|-------------------|-------------|
| Longitud mínima   | 12 caracteres |
| Mayúscula         | Requerida |
| Minúscula         | Requerida |
| Dígito            | Requerido |
| Símbolo especial  | Requerido |

### Flujo seguro

```
Usuario ingresa contraseña en SecurePasswordInput
        │
        ▼ (solo en core/services)
PasswordHasher.hash_password(plain)
        │  valida fortaleza
        │  verifica no-doble-hash
        │  bcrypt.hashpw(plain.encode(), salt)
        ▼
hash_bcrypt → se guarda en DB
        │
        ▼ (NUNCA se propaga a UI)
```

### Rehash automático
Si el número de rounds aumenta por política, el sistema rehashea silenciosamente en el próximo login exitoso.

### Anti-timing attack
En login, si el email no existe se ejecuta una verificación bcrypt dummy para igualar el tiempo de respuesta y evitar que un atacante deduzca si el email está registrado.

---

## 4. Cifrado de Campos PII (Fernet AES-128)

### Qué se cifra

| Campo         | Tabla         | Almacenado como |
|---------------|---------------|-----------------|
| nombre        | usuarios      | `nombre_enc`    |
| apellido      | usuarios      | `apellido_enc`  |
| email         | usuarios      | `email_enc`     |
| nombre        | clientes      | `nombre_enc`    |
| telefono      | clientes      | `telefono_enc`  |
| email         | clientes      | `email_enc`     |
| notas         | clientes      | `notas_enc`     |

### Algoritmo

- **Fernet** (AES-128-CBC + HMAC-SHA256) — de la librería `cryptography`.
- Formato de token versionado: `v1:<key_id>:<fernet_token>`
- El `key_id` permite descifrar con claves anteriores tras rotación.

### Búsqueda sin descifrado masivo

El email se indexa mediante **HMAC-SHA256** con un salt de namespace fijo:

```python
email_idx = hmac.new(b"metodobase_email_idx_v1", email.encode(), sha256).hexdigest()
```

Esto permite búsqueda por email exacto en O(1) sin descifrar todos los registros. El resultado es determinista pero no es una contraseña; solo aplica para búsqueda exacta.

---

## 5. Gestión de Claves de Cifrado

### Jerarquía de prioridad

```
1. Variable de entorno METODO_BASE_MASTER_KEY   ← producción / CI
2. Archivo ~/.metodobase/keys/mb_keys.json       ← desarrollo local
```

### Rotación de clave

```bash
# Rotar la clave activa (la anterior queda en 'previous' para descifrado)
python -c "
from core.services.key_manager import KeyManager
km = KeyManager()
km.rotate_key()
print('Clave rotada. Recifra los datos con la nueva clave.')
"
```

### ⚠️ Advertencias críticas

- **Nunca** embeber la clave en el código fuente o en el ejecutable empaquetado.
- **Nunca** committing `mb_keys.json` al repositorio — añadirlo a `.gitignore`.
- Si la clave se pierde, los datos cifrados **no se pueden recuperar**. Hacer backup cifrado de la clave por separado.
- En entornos CI/CD usar secretos de sistema (GitHub Secrets, Vault, AWS KMS).

---

## 6. Flujo de Autenticación y Registro

```
Splash Screen
    │
    ▼
Wizard Onboarding (primera vez)
    │
    ▼
Validación de Licencia
    │
    ▼
VentanaAuth (Login / Registro)
    │   ├── Login: email + password → AuthService.login()
    │   │         └─ respuesta genérica ante error (anti-enumeración)
    │   └── Registro: nombre, apellido, email, password ×2
    │             └─ DialogoPrivacidad (consentimiento obligatorio)
    │             └─ AuthService.registrar()
    │             └─ Pantalla ID único (mostrado 1 vez, advertencia UX)
    │                     └─ Clipboard se limpia auto en 60 s
    ▼
MainWindow (sesión activa)
```

### Datos expuestos a la UI tras autenticación

```python
@dataclass(frozen=True)
class SesionActiva:
    id_usuario: str      # UUID
    nombre_display: str  # Solo primer nombre
    rol: str             # 'admin' | 'usuario' | 'gym'
    # NUNCA: password_hash, email, apellido, tokens cifrados
```

---

## 7. Exportación Segura

### Campos permitidos en exportación

```python
_CLIENTE_PUBLIC_FIELDS = {
    "nombre", "edad", "peso_kg", "estatura_cm",
    "grasa_corporal_pct", "objetivo", "nivel_actividad",
}
```

### Campos NUNCA exportados

- `email`, `email_enc`, `nombre_enc`, `password_hash`
- Cualquier campo con sufijo `_enc` o `_idx`
- Tokens Fernet, IDs internos, notas\_enc

### Flujo de exportación

```
Usuario hace clic en "Exportar CSV/Excel"
        │
        ▼
DialogoConfirmacionExportacion (obligatorio)
  • "Solo se incluyen campos públicos"
  • "No se exportan contraseñas ni datos cifrados"
  • "El archivo no estará cifrado — guárdalo en lugar seguro"
        │
        ▼
filtrar_campos_cliente_export(cliente)  → ExportadorMultiformato
        │
        ▼
Archivo CSV/Excel sin datos sensibles
```

---

## 8. Checklist de Seguridad (OWASP Top 10 aplicado)

| # | Riesgo OWASP                        | Mitigación implementada |
|---|-------------------------------------|------------------------|
| 1 | Broken Access Control               | Sesión activa con rol; UI nunca accede a DB directamente |
| 2 | Cryptographic Failures              | bcrypt + Fernet; sin MD5/SHA1 para contraseñas |
| 3 | Injection                           | SQLite con parámetros `?` en todas las queries; sin SQL dinámico |
| 4 | Insecure Design                     | Separación UI/Core/DB; zero-trust desde UI |
| 5 | Security Misconfiguration           | Claves en env vars / archivo fuera del repo; PRAGMA foreign_keys=ON |
| 6 | Vulnerable Components               | bcrypt directo (no passlib 1.7.4 incompatible con bcrypt 4.x) |
| 7 | Auth & Identity Failures            | Política de contraseña fuerte; rehash automático; dummy timing |
| 8 | Software & Data Integrity           | Tokens Fernet con HMAC-SHA256 integrado; key_id versionado |
| 9 | Security Logging Failures           | Logs nunca incluyen nombre, email ni contraseñas |
| 10| SSRF                                | No hay llamadas a URLs externas en paths sensibles |

---

## 9. Widgets UX de Seguridad Implementados

### `SecurePasswordInput`
- `QLineEdit` en modo `Password` por defecto.
- Botón ojo (mostrar/ocultar) con `QLineEdit.Normal` / `QLineEdit.Password`.
- Barra de fortaleza visual: Débil → Aceptable → Fuerte → Muy fuerte.
- Cálculo de fortaleza **local** (nunca envía el texto a ningún servicio).
- `value()` / `clear()` — la contraseña se limpia en memoria tras usarse una vez.

### `VentanaAuth`
- Stack de 3 paneles: Login → Registro → Confirmación.
- ID de usuario mostrado **una sola vez** con aviso de privacidad.
- Botón "Copiar ID" limpia el portapapeles automáticamente en 60 s.
- Countdown de 30 s en pantalla de confirmación.
- Mensajes de error en login son **genéricos** (no revelan si el email existe).

### `DialogoPrivacidad`
- Modal obligatorio antes del registro.
- Texto con scroll: qué datos, cómo se protegen, para qué se usan, derechos.
- Solo `Aceptar` habilita el flujo de registro; `Rechazar` aborta.

---

## 10. Recomendaciones de Mantenimiento

### Rotación periódica de claves
- Rotar la clave Fernet cada 6–12 meses en producción.
- Tras rotar, ejecutar script de re-cifrado masivo de registros existentes.
- Conservar clave anterior en `previous` array hasta que todos los registros se re-cifren.

### Backup de clave
```bash
# Backup cifrado de la clave maestra (con GPG o similar)
gpg --symmetric --cipher-algo AES256 ~/.metodobase/keys/mb_keys.json
# Guardar el .gpg en ubicación separada del ejecutable y la DB
```

### Auditoría de cuentas
- Revisar `ultimo_acceso` periódicamente para detectar cuentas inactivas.
- Desactivar cuentas con `GestorUsuarios.desactivar_usuario(id)` en lugar de eliminar.
- Los datos desactivados pueden eliminarse físicamente a petición (GDPR/LGPD: derecho al olvido).

### Actualización de rounds bcrypt
- Si el hardware mejora, aumentar `rounds` en `PasswordHasher(rounds=14)`.
- El rehash automático actualizará los hashes en el próximo login de cada usuario.

### Dependencias
```bash
# Verificar vulnerabilidades de dependencias
pip install safety
safety check -r requirements.txt
```

---

## 11. Variables de Entorno

| Variable                   | Descripción                                          | Obligatoria |
|---------------------------|------------------------------------------------------|-------------|
| `METODO_BASE_MASTER_KEY`  | Clave Fernet base64 para cifrado de campos PII       | No (usa archivo local si ausente) |

Generar una nueva clave:
```python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
# Copiar el output como valor de METODO_BASE_MASTER_KEY
```

---

## 12. Estructura de Archivos de Seguridad

```
core/services/
  auth_service.py          ← Autenticación, sesión, registro
  crypto_service.py        ← Cifrado/descifrado Fernet
  key_manager.py           ← Gestión y rotación de claves
  password_hasher.py       ← bcrypt hash + validación de política

src/
  gestor_usuarios.py       ← DB tabla usuarios (PII cifrado)

ui_desktop/pyside/
  ventana_auth.py          ← UI Login + Registro (PySide6)
  ventana_privacidad.py    ← Modal consentimiento GDPR
  widgets/
    secure_password_input.py  ← Widget contraseña + barra fortaleza

tests/services/
  test_auth_service.py     ← 12 tests de autenticación y PII
  test_crypto_service.py   ← 3 tests de cifrado/descifrado
  test_password_hasher.py  ← 3 tests de hashing y política
  test_export_filter.py    ← 1 test de filtrado seguro de exportación
```

---

*Documento mantenido por el equipo técnico de Método Base. Revisión recomendada cada 6 meses o ante cambio de dependencias de seguridad.*
