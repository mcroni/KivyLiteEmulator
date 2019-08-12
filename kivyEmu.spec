# -*- mode: python -*-
from kivy_deps import sdl2, glew

block_cipher = None


a = Analysis(['main.py'],
             pathex=['C:\\Users\\MCRONI\\PycharmProjects\\kivyEmu'],
             binaries=[],
             datas=[],
             hiddenimports=['kivymd.theming', 'kivymd', 'kivymd.selectioncontrols', 'kivymd.card', 'kivymd.tabs', 'kivymd.menu','plyer','plyer.platforms','plyer.platforms.win','plyer.platforms.win.filechooser'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='kivyEmi',
          debug=False,
          strip=False,
          upx=True,
          console=True )

coll = COLLECT(exe, Tree('.'),
               a.binaries,
               a.zipfiles,
               a.datas,
               *[Tree(p) for p in (sdl2.dep_bins + glew.dep_bins)],
               strip=False,
               upx=True,
               name='kivyemu')
