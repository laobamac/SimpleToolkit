# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['D:\\SimpleToolkit\\Scripts\\gui_get_hw_info.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('HDSupportInfo.list', '.'),
        ('HDASupportInfo.list', '.'),
        ('GPUSupportInfo.list', '.'),
        ('ETHSupportInfo.list', '.')
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='gui_get_hw_info',
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
    icon=['D:\\SimpleToolkit\\Scripts\\gui_get_hw_info.ico'],
)
