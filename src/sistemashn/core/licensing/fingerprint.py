"""Huella de la máquina para verificar licencias offline (T1.4).

En Windows combina el `MachineGuid` del registro (`HKLM\\SOFTWARE\\Microsoft\\Cryptography`)
con el número de serie de volumen del disco del sistema (`GetVolumeInformationW`). Fuera de
Windows no hay un equivalente igual de estable en este proyecto: se usa `platform.node()`
como resguardo, documentado como **no apto para producción** (cambia si cambia el hostname).
"""

import ctypes
import hashlib
import os
import platform
import sys


def _machine_guid_windows() -> str:
    import winreg

    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography") as key:
        valor, _ = winreg.QueryValueEx(key, "MachineGuid")
        return str(valor)


def _volume_serial_windows() -> str:
    unidad_sistema = os.environ.get("SystemDrive", "C:")  # noqa: SIM112 (nombre real en Windows)
    raiz = unidad_sistema + "\\"

    nombre_volumen = ctypes.create_unicode_buffer(261)
    nombre_sistema_archivos = ctypes.create_unicode_buffer(261)
    numero_serie = ctypes.c_uint(0)
    longitud_max_componente = ctypes.c_uint(0)
    banderas_sistema_archivos = ctypes.c_uint(0)

    ok = ctypes.windll.kernel32.GetVolumeInformationW(  # type: ignore[attr-defined]
        ctypes.c_wchar_p(raiz),
        nombre_volumen,
        ctypes.sizeof(nombre_volumen),
        ctypes.byref(numero_serie),
        ctypes.byref(longitud_max_componente),
        ctypes.byref(banderas_sistema_archivos),
        nombre_sistema_archivos,
        ctypes.sizeof(nombre_sistema_archivos),
    )
    if not ok:
        raise OSError("GetVolumeInformationW falló al leer el volumen del sistema")
    return f"{numero_serie.value:08X}"


def machine_fingerprint() -> str:
    """Sha256 hex (64 caracteres) estable de la máquina actual.

    En Windows: `MachineGuid` + número de serie del volumen del sistema. Fuera de Windows
    se usa `platform.node()` como resguardo documentado, no apto para producción.
    """
    if sys.platform == "win32":
        crudo = _machine_guid_windows() + _volume_serial_windows()
    else:
        crudo = f"fallback-no-windows:{platform.node()}"
    return hashlib.sha256(crudo.encode("utf-8")).hexdigest()
