# Guia de Emision de Keys de Licencia

Este documento explica como generar keys de activacion desde tu PC emisora.

## Resumen del flujo

1. El cliente abre la app y te comparte su `ID instalacion` (sale en la ventana de activacion).
2. En tu PC emisora ejecutas el generador.
3. Seleccionas periodo `3`, `6`, `9` o `12` meses.
4. Generas la key y se la escribes al cliente en su ventana de activacion.

## Requisitos importantes

- El generador esta bloqueado por defecto.
- Debes habilitarlo en tu PC con `METODO_BASE_EMISOR=1`.
- En builds cliente (`.exe`) el generador esta bloqueado siempre.
- El valor de `METODO_BASE_SALT` debe ser el mismo en emisor y cliente para que la key sea valida.

## Linux (Pop!_OS / bash)

Desde la raiz del proyecto:

```bash
cd /ruta/a/MetodoBase-Full
export METODO_BASE_EMISOR=1
export METODO_BASE_SALT="TU_SALT_PRIVADO"
python3 -m core.licencia
```

Comando en una sola linea:

```bash
METODO_BASE_EMISOR=1 METODO_BASE_SALT="TU_SALT_PRIVADO" python3 -m core.licencia
```

Al terminar (opcional, recomendado):

```bash
unset METODO_BASE_EMISOR
unset METODO_BASE_SALT
```

## Windows PowerShell

Desde la raiz del proyecto:

```powershell
Set-Location "C:\ruta\MetodoBase-Full"
$env:METODO_BASE_EMISOR = "1"
$env:METODO_BASE_SALT = "TU_SALT_PRIVADO"
python -m core.licencia
```

Si usas `py`:

```powershell
py -m core.licencia
```

Limpiar variables al terminar (recomendado):

```powershell
Remove-Item Env:METODO_BASE_EMISOR
Remove-Item Env:METODO_BASE_SALT
```

## Uso del generador

Al ejecutar `python -m core.licencia`:

1. Elige periodo:
1. `1` -> 3 meses
1. `2` -> 6 meses
1. `3` -> 9 meses
1. `4` -> 12 meses
1. Ingresa el `ID instalacion` del cliente
1. El sistema imprime la `Key activacion`

## Errores comunes

- `Generador de keys deshabilitado en este entorno`
  - Falta definir `METODO_BASE_EMISOR=1`, o estas en un binario cliente.

- `Key invalida para esta instalacion o para el periodo seleccionado`
  - El `ID instalacion` no coincide.
  - El periodo seleccionado en cliente no coincide con el usado al generar.
  - `METODO_BASE_SALT` no coincide entre emisor y cliente.

## Seguridad recomendada

- No distribuyas tu valor de `METODO_BASE_SALT`.
- No incluyas `METODO_BASE_EMISOR=1` en instaladores cliente.
- Genera keys solo desde tu PC emisora.

