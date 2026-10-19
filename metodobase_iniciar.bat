@echo off
setlocal
REM Launch the complete desktop bundle. Never install Python or dependencies.
set "DESKTOP_DIR=%~dp0"
if not exist "%DESKTOP_DIR%MetodoBase.exe" set "DESKTOP_DIR=%~dp0dist\MetodoBase\"
if not exist "%DESKTOP_DIR%MetodoBase.exe" (
  echo MetodoBase.exe is missing. Extract the complete verified desktop package. 1>&2
  exit /b 2
)
if not exist "%DESKTOP_DIR%_internal\" (
  echo The _internal dependency directory is missing. 1>&2
  exit /b 2
)
if not exist "%DESKTOP_DIR%build-manifest.json" (
  echo The desktop package manifest is missing. 1>&2
  exit /b 2
)
"%DESKTOP_DIR%MetodoBase.exe"
exit /b %errorlevel%
