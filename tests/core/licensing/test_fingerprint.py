"""Prueba de la huella de máquina (T1.4)."""

from sistemashn.core.licensing.fingerprint import machine_fingerprint


def test_machine_fingerprint_es_hex_de_64_caracteres_y_estable() -> None:
    huella1 = machine_fingerprint()
    huella2 = machine_fingerprint()
    assert len(huella1) == 64
    assert all(c in "0123456789abcdef" for c in huella1)
    assert huella1 == huella2
