from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files("customtkinter")
a = Analysis(["src/main.py"], pathex=["."], binaries=[], datas=datas,
             hiddenimports=[], hookspath=[], hooksconfig={}, runtime_hooks=[],
             excludes=[], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name="Auto-Facturas",
          debug=False, bootloader_ignore_signals=False, strip=False, upx=True,
          console=False, disable_windowed_traceback=False)
