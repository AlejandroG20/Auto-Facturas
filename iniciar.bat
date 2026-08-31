@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
  echo No se encontro el entorno virtual .venv.
  echo Crea el entorno con: python -m venv .venv
  echo Instala las dependencias con: .venv\Scripts\python.exe -m pip install -r requirements.txt
  pause
  exit /b 1
)
".venv\Scripts\pythonw.exe" -c "import customtkinter, keyboard, pyautogui" 2>nul
if errorlevel 1 (
  echo Faltan dependencias. Ejecuta:
  echo .venv\Scripts\python.exe -m pip install -r requirements.txt
  pause
  exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" -m src.main
