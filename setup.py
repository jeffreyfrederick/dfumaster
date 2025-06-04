from setuptools import setup

APP = ['dfumaster/app.py']
DATA_FILES = ['ipsw', 'dfumaster/macvdmtool/macvdmtool']
OPTIONS = {
    'argv_emulation': True,
    'iconfile': 'icon.icns',  # Optional icon
    'packages': ['PySide6'],
    'plist': {
        'CFBundleName': 'DFU Master',
        'CFBundleDisplayName': 'DFU Master',
        'CFBundleIdentifier': 'com.yourcompany.dfumaster',
        'CFBundleVersion': '1.0.0',
        'LSUIElement': True,  # Hide menu bar if desired
    },
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
