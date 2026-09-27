"""Imprime `sistemashn.__version__` en stdout.

Usado por `scripts\\build_windows.bat` para leer la versión global del sistema sin
tener que pasar un one-liner con comillas anidadas por `cmd.exe` (frágil: el
parser de `cmd` rompe las comillas internas al combinarlas con `;` dentro de
backticks de `for /f`).
"""

from sistemashn import __version__

print(__version__)
