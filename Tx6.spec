# -*- mode: python ; coding: utf-8 -*-
import os

PATCH_PRINT_EXE = os.path.abspath('A-PatchPrint.exe')
PS_AUTO_EXE     = os.path.abspath('PS_Auto_GUI1.exe')

binaries = []
if os.path.exists(PATCH_PRINT_EXE):
    binaries.append((PATCH_PRINT_EXE, 'tools'))
if os.path.exists(PS_AUTO_EXE):
    binaries.append((PS_AUTO_EXE, 'tools'))

a = Analysis(
    ['app.py'],
    pathex=[os.path.abspath('.')],
    binaries=binaries,
    datas=[
        ('app_icon.png', '.'),
        ('Xổ Số.mp3', '.'),
        ('gui.py', '.'),
        ('tai_xiu_game.py', '.'),
        ('tx_network.py', '.'),
        ('security.py', '.'),
        ('logic.py', '.'),
        ('server.py', '.'),
        ('color_reader.py', '.'),
        ('clipboard_bridge.py', '.'),
        ('auto_workflow.py', '.'),
        ('ui_components.py', '.'),
        ('order_db.py', '.'),
    ],
    hiddenimports=[
        'flask', 'flask.json', 'flask.wrappers', 'flask.cli',
        'werkzeug', 'werkzeug.serving', 'werkzeug.routing', 'werkzeug.exceptions',
        'PySide6', 'PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets',
        'PySide6.QtNetwork', 'PySide6.QtMultimedia', 'PySide6.QtMultimediaWidgets',
        'PySide6.QtPrintSupport', 'PySide6.QtSvg', 'PySide6.QtOpenGL',
        'PySide6.QtOpenGLWidgets', 'shiboken6',
        'websockets', 'websockets.server', 'websockets.connection',
        'websockets.legacy', 'websockets.legacy.server',
        'asyncio', 'asyncio.events', 'asyncio.base_events',
        'socket', 'threading', 'requests', 'requests.adapters', 'urllib3', 'certifi',
        'keyboard', 'psutil', 'pyautogui', 'pyperclip', 'pyscreeze',
        'PIL', 'PIL.Image', 'PIL.ImageFilter', 'PIL.ImageEnhance', 'PIL.ImageGrab',
        'cv2', 'bs4', 'yt_dlp',
        'win32gui', 'win32con', 'win32process', 'win32api', 'winreg',
        'winsound', 'ctypes', 'ctypes.wintypes',
        'json', 'hashlib', 'datetime', 'traceback', 'importlib', 'sqlite3',
        'tai_xiu_game', 'tx_network', 'gui', 'logic', 'security',
        'server', 'color_reader', 'auto_workflow', 'ui_components', 'order_db',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt5', 'PyQt6', 'tkinter', 'matplotlib', 'scipy'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name='Tx6',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[
        'Qt6Multimedia.dll', 'Qt6MultimediaWidgets.dll',
        'Qt6Network.dll', 'Qt6Core.dll', 'Qt6Gui.dll',
        'Qt6Widgets.dll', 'python310.dll',
    ],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=True,
    icon='app_icon.png',
)
