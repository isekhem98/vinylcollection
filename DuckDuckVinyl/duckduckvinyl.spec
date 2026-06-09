# -*- mode: python ; coding: utf-8 -*-
# DuckDuckVinyl – PyInstaller spec
# Run with:  pyinstaller duckduckvinyl.spec

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect Flask and Jinja2 data files (templates, static assets bundled in the packages)
flask_datas   = collect_data_files('flask')
jinja2_datas  = collect_data_files('jinja2')
markupsafe_datas = collect_data_files('markupsafe')

a = Analysis(
    ['run.py'],                          # entry-point
    pathex=['.'],                        # add project root to import path
    binaries=[],
    datas=(
        flask_datas
        + jinja2_datas
        + markupsafe_datas
        + [('templates', 'templates')]
        # Include data.json so the bundled EXE can seed an empty DB on first run
        + [('data.json', '.')]
    ),
    hiddenimports=[
        # Flask internals that PyInstaller sometimes misses
        'flask',
        'flask.templating',
        'jinja2',
        'jinja2.ext',
        'markupsafe',
        'werkzeug',
        'werkzeug.serving',
        'werkzeug.routing',
        'werkzeug.exceptions',
        'werkzeug.utils',
        'werkzeug.wrappers',
        'werkzeug.middleware.proxy_fix',
        # App modules
        'webapp',
        'database',
        'discogs_client',
        # stdlib extras sometimes missed
        'sqlite3',
        'queue',
        'threading',
        'webbrowser',
        'socket',
        'pathlib',
        'logging',
        'logging.handlers',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # These are only needed for Heroku/Postgres deployment; exclude to keep EXE small
        'sqlalchemy',
        'psycopg2',
        'gunicorn',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='DuckDuckVinyl',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,               # compress with UPX if available (smaller EXE)
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,           # set to False to hide the console window (but harder to debug)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='icon.ico',      # uncomment and provide an .ico file to set a custom icon
)
