"""Genera un Excel de catálogo demo con productos realistas de autorepuestos (T2.5).

Uso:
    evn\\Scripts\\python.exe scripts\\generar_catalogo_demo.py demo-catalogo-1000.xlsx [--count 1000]

Antes de importar el archivo generado deben existir:
    - Categorías: ver `CATEGORIAS_REQUERIDAS`.
    - Unidades: `UND` (unidad) y `LTR` (litro).
"""

from __future__ import annotations

import argparse
from decimal import Decimal
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font

CATEGORIAS_REQUERIDAS: tuple[str, ...] = (
    "Frenos",
    "Motor",
    "Suspensión",
    "Eléctrico",
    "Filtros",
    "Lubricantes",
    "Transmisión",
    "Carrocería",
    "Refrigeración",
    "Accesorios",
)

UNIDADES_REQUERIDAS: tuple[str, ...] = ("UND", "LTR")

# (nombre base, categoría, unidad, precio base)
_TIPOS_DE_PARTE: tuple[tuple[str, str, str, str], ...] = (
    ("Filtro de aceite", "Filtros", "UND", "95.00"),
    ("Filtro de aire", "Filtros", "UND", "180.00"),
    ("Filtro de combustible", "Filtros", "UND", "150.00"),
    ("Bujía de encendido", "Eléctrico", "UND", "65.00"),
    ("Pastilla de freno delantera", "Frenos", "UND", "620.00"),
    ("Pastilla de freno trasera", "Frenos", "UND", "540.00"),
    ("Disco de freno", "Frenos", "UND", "980.00"),
    ("Banda de distribución", "Motor", "UND", "750.00"),
    ("Aceite de motor 20W-50", "Lubricantes", "LTR", "185.00"),
    ("Aceite de transmisión", "Lubricantes", "LTR", "210.00"),
    ("Refrigerante para radiador", "Refrigeración", "LTR", "160.00"),
    ("Amortiguador delantero", "Suspensión", "UND", "1450.00"),
    ("Amortiguador trasero", "Suspensión", "UND", "1320.00"),
    ("Batería 12V", "Eléctrico", "UND", "2450.00"),
    ("Correa de alternador", "Motor", "UND", "310.00"),
    ("Kit de embrague", "Transmisión", "UND", "3200.00"),
    ("Radiador de aluminio", "Refrigeración", "UND", "2850.00"),
    ("Sensor de oxígeno", "Eléctrico", "UND", "890.00"),
    ("Espejo lateral", "Carrocería", "UND", "560.00"),
    ("Bomba de agua", "Motor", "UND", "980.00"),
    ("Terminal de dirección", "Suspensión", "UND", "420.00"),
    ("Rótula de suspensión", "Suspensión", "UND", "380.00"),
    ("Bandín (banda multicanal)", "Motor", "UND", "295.00"),
    ("Foco delantero H4", "Eléctrico", "UND", "145.00"),
    ("Tapón de aceite", "Accesorios", "UND", "35.00"),
)

_MARCAS: tuple[str, ...] = (
    "Toyota",
    "Nissan",
    "Honda",
    "Hyundai",
    "Kia",
    "Mazda",
    "Chevrolet",
    "Ford",
    "Mitsubishi",
    "Suzuki",
)


def generar_filas(count: int = 1000) -> list[dict[str, object]]:
    """Genera `count` filas de producto (dicts) listas para escribir en Excel."""
    filas: list[dict[str, object]] = []
    tasas = (Decimal("0"), Decimal("15"), Decimal("18"))
    for i in range(count):
        tipo, categoria, unidad, precio_base = _TIPOS_DE_PARTE[i % len(_TIPOS_DE_PARTE)]
        marca = _MARCAS[(i // len(_TIPOS_DE_PARTE)) % len(_MARCAS)]
        codigo = f"REP-{i:05d}"
        nombre = f"{tipo} {marca}"
        precio = (Decimal(precio_base) + Decimal(i % 50) * Decimal("2.35")).quantize(
            Decimal("0.01")
        )
        tasa = tasas[i % len(tasas)]
        activo = "no" if i % 97 == 0 else "si"
        filas.append(
            {
                "codigo": codigo,
                "codigo_barras": f"750{i:09d}",
                "nombre": nombre,
                "descripcion": f"{nombre} — repuesto de reposición, calidad garantizada",
                "categoria": categoria,
                "unidad": unidad,
                "tasa_isv": int(tasa),
                "precio_venta": float(precio),
                "stock_minimo": (i % 10) + 1,
                "activo": activo,
            }
        )
    return filas


def escribir_demo(path: str | Path, count: int = 1000) -> None:
    filas = generar_filas(count)
    wb = Workbook()
    ws = wb.active
    ws.title = "Productos"
    columnas = (
        "codigo",
        "codigo_barras",
        "nombre",
        "descripcion",
        "categoria",
        "unidad",
        "tasa_isv",
        "precio_venta",
        "stock_minimo",
        "activo",
    )
    ws.append(columnas)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for fila in filas:
        ws.append([fila[col] for col in columnas])
    wb.save(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", help="Ruta de salida del archivo .xlsx")
    parser.add_argument("--count", type=int, default=1000, help="Cantidad de productos (1000)")
    args = parser.parse_args()

    escribir_demo(args.path, args.count)

    print(f"Generado {args.path} con {args.count} productos.")
    print("Antes de importar deben existir estas categorías:")
    for categoria in CATEGORIAS_REQUERIDAS:
        print(f"  - {categoria}")
    print("Y estas unidades:")
    for unidad in UNIDADES_REQUERIDAS:
        print(f"  - {unidad}")


if __name__ == "__main__":
    main()
