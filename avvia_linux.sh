#!/usr/bin/env bash
# Script per avvio rapido su Linux con doppio clic o da terminale

cd "$(dirname "$0")"

echo "=============================================="
echo "       Avvio Finance Tracker Pro"
echo "=============================================="

if ! command -v python3 &> /dev/null; then
    echo "[ERRORE] Python 3 non è installato sul tuo sistema."
    exit 1
fi

if [ ! -d "venv" ]; then
    echo "==> Primo avvio: creazione ambiente virtuale..."
    python3 -m venv venv
    source venv/bin/activate
    echo "==> Installazione librerie..."
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

echo "==> Avvio dell'applicazione..."
python3 main.py
