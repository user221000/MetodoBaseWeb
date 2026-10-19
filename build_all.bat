@echo off
setlocal
REM No cleanup, install, compiler lookup or source replacement in this wrapper.
if not defined METODOBASE_BUILD_PYTHON (
  echo Set METODOBASE_BUILD_PYTHON to the reviewed temporary Python executable. 1>&2
  exit /b 2
)
if not exist "%METODOBASE_BUILD_PYTHON%" (
  echo The selected build Python executable does not exist. 1>&2
  exit /b 2
)
"%METODOBASE_BUILD_PYTHON%" "%~dp0build.py" --zip %*
exit /b %errorlevel%
