# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

import os
import sys

datas = []
for icon_file in ['icon.ico', 'icon.png', 'icon.icns', 'icon.svg']:
    if os.path.exists(icon_file):
        datas.append((icon_file, '.'))

binaries = []
hiddenimports = ['PIL._tkinter_finder']

# Raccoglie moduli e risorse per CustomTkinter e Matplotlib
tmp_ret = collect_all('customtkinter')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

tmp_ret = collect_all('matplotlib')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

if sys.platform == 'darwin' and os.path.exists('icon.icns'):
    icon_path = 'icon.icns'
elif sys.platform.startswith('win') and os.path.exists('icon.ico'):
    icon_path = 'icon.ico'
elif os.path.exists('icon.ico'):
    icon_path = 'icon.ico'
else:
    icon_path = None

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='FinanceTracker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path,
)

if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='FinanceTracker.app',
        icon='icon.icns' if os.path.exists('icon.icns') else None,
        bundle_identifier='com.financetracker.app',
    )