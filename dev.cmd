@echo off
setlocal enableextensions enabledelayedexpansion

REM ----- Args -----
if "%~1"=="" goto :HELP
set "TASK=%~1"
shift
set "MSG=%*"

REM ----- Activate venv -----
if not exist ".\.venv\Scripts\activate.bat" (
  echo [ERROR] Virtual env not found. Run: python -m venv .venv
  exit /b 1
)
call ".\.venv\Scripts\activate.bat"

REM Ensure local packages import (backend, ml, etc.)
set "PYTHONPATH=."

REM ----- Tasks -----
if /I "%TASK%"=="server" (
  uvicorn --app-dir . backend.app.main:app --host 127.0.0.1 --port 8000 --reload
  goto :EOF
)

if /I "%TASK%"=="migrate" (
  python -m alembic upgrade head
  goto :EOF
)

if /I "%TASK%"=="train" (
  python -m ml.training.train_classifier
  goto :EOF
)

if /I "%TASK%"=="eval" (
  python -m ml.training.evaluate
  goto :EOF
)

if /I "%TASK%"=="frontend" (
  pushd frontend
  call npm install
  call npm run build
  popd
  goto :EOF
)

:HELP
echo Usage: dev ^<task^>
echo   server ^| migrate ^| train ^| eval ^| frontend
exit /b 0
