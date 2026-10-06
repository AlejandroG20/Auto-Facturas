@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
  echo Auto-Facturas todavia no esta preparado en este equipo.
  echo.
  echo Abre PowerShell en esta carpeta y ejecuta, en este orden:
  echo   python -m venv .venv
  echo   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
  echo.
  pause
  exit /b 1
)
".venv\Scripts\pythonw.exe" -c "import customtkinter, keyboard, pyautogui" 2>nul
if errorlevel 1 (
  echo Faltan componentes necesarios para abrir Auto-Facturas.
  echo.
  echo Abre PowerShell en esta carpeta y ejecuta:
  echo   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
  echo.
  pause
  exit /b 1
)
start "Auto-Facturas" "%~dp0.venv\Scripts\pythonw.exe" -m src.main
