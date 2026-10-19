Revisión independiente del candidato desktop construido desde `9f3f32e5fffa61d453f7bccfe27d91f24a13d561`, realizada el 19 de octubre de 2026 en `F:MetodoBaseWeb-desktop-build-lf-20261019`. Se acepta el alcance demostrado de **onedir Windows x64 sin firma, ZIP íntegro e inicio del diagnóstico Qt offscreen**. Esto no acredita publicación comercial ni instalación o flujos de negocio.

El verificador propio produjo **39 comprobaciones verdes** y no reconstruyó ni modificó el artefacto. Comparó los bytes de las 1688 fuentes con los blobs del commit exacto, sin depender de `git status`. Las fotografías completas antes/después de fuentes, bundle, ZIP, entradas Inno y hashes de configuración Git son iguales. El checkout del artefacto permaneció limpio.

| Elemento | Resultado independiente |
| --- | --- |
| ZIP | `dist/MetodoBase_v2.0.0_win32.zip`, 122774966 bytes |
| SHA-256 ZIP | `a3fdb846e51b027ff73f15fff1dcedf0aaf2898837e780d02d4184b85a0c6b46` |
| Bundle / ZIP | 1215 archivos declarados más `build-manifest.json`: 1216 miembros exactos, 254969990 bytes sin comprimir |
| Integridad | CRC y SHA-256/tamaño de cada miembro iguales al bundle; sin nombres duplicados, colisiones de mayúsculas, rutas inseguras ni enlaces |
| Ejecutable | PE32+ AMD64, subsistema Windows GUI; tabla de certificados ausente |
| Binarios nativos | 217 EXE/DLL/PYD, todos con cabecera PE AMD64 |
| Recursos | 34 recursos de fuente iguales por bytes; Inter regular/medium/bold y plugins Qt Windows/offscreen presentes |
| Código embebido | 10 módulos de entrada, autenticación, licencias, catálogo, claves, perfiles y UI iguales estructuralmente a la compilación del fuente exacto |
| Inno preparado | 1216 fuentes explícitas y destinos exactos; versión 2.0.0, commit y hash del manifiesto coinciden |
| Diagnóstico independiente | EXE empaquetado, exit 0, Qt offscreen y `VentanaLoginUnificada` construida; recibo con nonce privado comprobado |

El código embebido se inspeccionó mediante el lector CArchive/PYZ de PyInstaller sin ejecutarlo. Se compararon recursivamente atributos de código, constantes, bytecode y tablas de líneas/excepciones; sólo se excluyó `co_filename`, que cambia al congelar. Los valores de constantes no se registran. No se pretende que diez módulos acrediten todos los flujos importables ni que esta comparación sustituya una reconstrucción reproducible.

El diagnóstico usó un perfil nuevo bajo Temp, con datos, HOME/USERPROFILE, APPDATA/LOCALAPPDATA y preferencia de tema separados. Sus archivos sintéticos se inventariaron sólo por ruta relativa, tamaño y hash, sin guardar claves o datos. Se eliminó el perfil al terminar. El recibo confirma bloqueo de sockets Python y `product_flow_executed=false`; **no acredita aislamiento de red del sistema operativo**, autenticación, registro, activación ni uso de planes. El hook sale antes de `main.py` y no acciona las señales de login/registro.

La inspección visual añadió un pendiente de distribución: `_internal/assets/design-reference.png` es una captura de referencia de diseño que muestra nombres y correos de apariencia personal. Una búsqueda literal en fuentes de producto no halló uso de ese archivo. **Su procedencia no está acreditada y no se afirma que sus identidades sean reales.** Conviene excluir el material de referencia de los recursos distribuidos o acreditar su procedencia antes de publicar. La inspección visual de `Pasted Image.png` y `Screenshot_2026-03-26_16-00-16.png` mostró iconos genéricos. FONDO, ICON y el logo son recursos de marca/imagen; esta revisión no acredita sus licencias de distribución. Los hashes y la observación están en [la evidencia de recursos](desktop-artifact-independent-resources-source.json).

El filtro de nombres no encontró .env, bases de datos, licencias de usuario, entornos ni claves privadas como archivos del payload. La excepción explícita `certifi/cacert.pem` es el conjunto de autoridades públicas idéntico al del entorno fijado, sin bloque PRIVATE KEY. **Ese filtro no es un escaneo exhaustivo de secretos embebidos en bytecode o binarios.** La autoridad HMAC desktop/rotación del puente de licencias SEC01 sigue pendiente; el mero empaquetado de código legado no la resuelve.

La preparación de Inno conserva AppId y compatibilidad x64 declarados, no contiene secciones [Run] ni [UninstallDelete] y no compila nada. Permanecen pendientes el compilador Inno fijado, comparación del instalador compilado contra este manifiesto, pruebas de instalación/actualización/desinstalación en Windows descartable, firma autorizada y verificación de identidad. No se ejecutó instalador, GUI visible, negocio, publicación ni aprovisionamiento. Linux y macOS conservan su soporte previsto y necesitan build y validación nativos.

El archivo de advertencias de PyInstaller tiene 326 entradas missing/excluded; la búsqueda por importadores de módulos propios (`core.`, `src.`, `ui_desktop.`, `config.`) no encontró entradas. No se interpretan las importaciones opcionales de terceros como pruebas de éxito funcional. El uso de funciones que no ejercita el diagnóstico sigue pendiente.

Se conservó la primera pasada del verificador, que marcó tres falsos positivos: dos parsers no consumían el BOM UTF-8 correcto de los .iss y la heurística marcaba el CA público de certifi. Se corrigió únicamente el verificador: lectura utf-8-sig y comprobación explícita de identidad del CA público. Se volvió a fotografiar y verificar todo, con otro perfil temporal para el diagnóstico. No cambió el artefacto ni se relajaron las comparaciones de bytes, manifiesto, rutas o CRC.

Evidencia reproducible, saneada y separada de producto:

- [Resultado y fotografías completas](desktop-artifact-independent-source.json).
- [Log final](desktop-artifact-independent.log).
- [Verificador final ejecutado en Temp, conservado como texto con bytes idénticos](desktop-artifact-independent-review-script.txt).
- [Primer resultado conservado](desktop-artifact-independent-initial-source.json), [log inicial](desktop-artifact-independent-initial.log) y [verificador inicial](desktop-artifact-independent-initial-review-script.txt).
- [Hash de las evidencias](desktop-artifact-independent-evidence-manifest.json).

La aceptación se limita a integridad/procedencia, contenido técnico del onedir/ZIP y construcción del widget Qt en el diagnóstico. **Publicación, privacidad completa, licencia comercial, instalador y firma siguen sin aprobación.**

