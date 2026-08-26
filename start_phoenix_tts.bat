@echo off
setlocal EnableExtensions EnableDelayedExpansion
set "ROOT=%~dp0"
set "RAIN_REAL=%ROOT%runtime\rainfall"
if not exist "%RAIN_REAL%\python\python.exe" set "RAIN_REAL=F:\cosyvoice-rainfall-v2\cosyvoice-rainfall"
set "RAIN="
set "RAIN_DRIVE="

if not exist "%RAIN_REAL%\python\python.exe" (
  echo Rainfall embedded python not found:
  echo %RAIN_REAL%\python\python.exe
  pause
  exit /b 1
)

for %%D in (R S T U V W X Y Z) do if not defined RAIN if not exist "%%D:\" (
  subst %%D: "%RAIN_REAL%" >nul 2>nul
  if exist "%%D:\python\python.exe" (
    set "RAIN=%%D:\"
    set "RAIN_DRIVE=%%D:"
  )
)

if not defined RAIN (
  echo Unable to create an ASCII runtime drive. Please free one drive letter from R: to Z: and try again.
  pause
  exit /b 1
)

set "PYTHON=%RAIN%python\python.exe"
set "ASR_PYTHON=%ROOT%runtime\asr\Scripts\python.exe"
if not exist "%ASR_PYTHON%" set "ASR_PYTHON=%PYTHON%"

for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":8090" ^| findstr "LISTENING"') do (
  taskkill /PID %%P /F >nul 2>nul
)

ping -n 2 127.0.0.1 >nul
set "PHOENIX_RAINFALL_HOME=!RAIN!"
set "PHOENIX_ASR_PYTHON=!ASR_PYTHON!"
start "" /b powershell.exe -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 3; Start-Process 'http://127.0.0.1:8090'" >nul 2>nul
pushd "!ROOT!"
"!PYTHON!" -m uvicorn app.backend.main:app --host 127.0.0.1 --port 8090
set "EXIT_CODE=!ERRORLEVEL!"
popd
if defined RAIN_DRIVE subst !RAIN_DRIVE! /D >nul 2>nul
exit /b !EXIT_CODE!
