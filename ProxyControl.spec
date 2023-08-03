# FILEPATH: c:\Workspace\python\ladder\ProxyControl.spec

import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files

# Get the path of the assets folder
assets_path = str(Path('App', 'assets'))

# Collect all the .ico files in the assets folder
data_files = collect_data_files(assets_path, include_py_files=False)

# Add the .ico files to the list of data files
for root, _, files in os.walk(assets_path):
    for file in files:
        if file.endswith('.ico'):
            data_files.append((os.path.join(root, file), root))

# Define the PyInstaller spec file
a = Analysis(['main.py'],
             pathex=[],
             binaries=[],
             datas=data_files,
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=None,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
          cipher=None)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='ProxyControl',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          upx_include=[],
          runtime_tmpdir=None,
          console=False,
          icon='App\\assets\\di.ico' )
