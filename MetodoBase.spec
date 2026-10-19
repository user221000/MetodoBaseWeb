# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import sys

ROOT = Path(SPECPATH).resolve()
sys.path.insert(0, str(ROOT))
from build import APP_NAME, HIDDEN_IMPORTS, collect_resources, read_version

a = Analysis([str(ROOT / "main.py")], pathex=[str(ROOT)], binaries=[], datas=collect_resources(ROOT),
             hiddenimports=list(HIDDEN_IMPORTS), hookspath=[],
             runtime_hooks=[str(ROOT / "scripts/desktop_runtime_hook.py")],
             excludes=["tkinter", "customtkinter"], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name=APP_NAME,
          debug=False, strip=False, upx=False, console=False, contents_directory="_internal")
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name=APP_NAME)
if sys.platform == "darwin":
    # Native .app remains available; signing/notarization and symlink archive
    # semantics require a macOS validation before publication.
    app = BUNDLE(coll, name=APP_NAME + ".app", version=read_version(ROOT), bundle_identifier="com.metodobase.desktop")
