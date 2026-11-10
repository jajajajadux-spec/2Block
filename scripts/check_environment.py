import sys

print(f"Python {sys.version.split()[0]} at {sys.executable}")
if sys.version_info < (3, 11):
    raise SystemExit("2Block needs Python 3.11 or newer")
try:
    import tkinter
except ImportError as error:
    print('Tk is not installed. Browser play still works; packaged installer dialogs need Tcl/Tk.')
else:
    print(f'Tk {tkinter.TkVersion} available for installer/error dialogs.')
print('Game rendering needs a WebGL-capable browser. Start with: python -m apps.server')
