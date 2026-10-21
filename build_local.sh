#!/usr/bin/env bash
# Script per compilare l'eseguibile Linux in locale con un solo comando

set -e

echo "==> 1. Installazione dipendenze e PyInstaller..."
pip install -r requirements.txt pyinstaller

echo "==> 2. Compilazione eseguibile (Standalone con icona)..."
pyinstaller --noconfirm main.spec

