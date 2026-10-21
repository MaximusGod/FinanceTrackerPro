@echo off
chcp 65001 >nul
title Finance Tracker Pro
cd /d "%~dp0"

echo ==============================================
echo       Avvio Finance Tracker Pro
echo ==============================================

python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERRORE] Python non e installato o non e configurato nel PATH di Windows.
    echo Per favore installa Python da https://www.python.org/
    echo Assicurati di selezionare la casella "Add Python to PATH" durante l'installazione.
    echo.
    pause
    exit /b
)

if not exist "venv" (
    echo ==> Primo avvio: configurazione dell'ambiente virtuale in corso...
    python -m venv venv
    call venv\Scripts\activate.bat
    echo ==> Installazione delle librerie necessarie...
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

echo ==> Avvio dell'applicazione...
python main.py
if %ERRORLEVEL% neq 0 (
    echo.
    echo [AVVISO] Si e verificato un errore durante l'esecuzione.
    pause
)
