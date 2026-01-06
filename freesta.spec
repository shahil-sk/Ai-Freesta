# In the EXE section, add icon parameter
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='freesta',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',  # For Windows - must be .ico [web:117]
)
