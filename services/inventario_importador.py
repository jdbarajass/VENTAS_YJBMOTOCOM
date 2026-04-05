"""
services/inventario_importador.py
Importa productos de inventario desde un archivo .xlsx.

Detecta los encabezados por palabras clave (case-insensitive) para ser
compatible con distintos formatos de Excel del usuario.
"""

from dataclasses import dataclass, field
from pathlib import Path

import openpyxl

from models.producto import Producto


# Palabras clave para identificar cada columna
_KW_SERIAL    = {"serial", "numero", "número", "n°", "no.", "#", "consecutivo"}
_KW_PRODUCTO  = {"nombre", "producto", "artículo", "articulo", "descripcion", "descripción", "item"}
_KW_COSTO     = {"costo", "precio", "valor"}
_KW_CANTIDAD  = {"cantidad", "stock", "bodega", "existencia", "unidades"}
_KW_BARRAS    = {"codigo", "código", "barras", "ean", "upc", "barra"}


@dataclass
class ResultadoInventario:
    productos: list[Producto] = field(default_factory=list)
    errores: list[str] = field(default_factory=list)
    total_leidos: int = 0


def _detectar_columnas(fila_headers: list) -> dict[str, int | None]:
    """
    Recibe una lista de valores de la fila de encabezados y retorna
    un dict {campo: índice_columna_0based | None}.
    """
    mapa: dict[str, int | None] = {
        "serial": None, "producto": None, "costo": None,
        "cantidad": None, "codigo_barras": None,
    }

    for idx, cell in enumerate(fila_headers):
        valor = str(cell or "").lower().strip()
        if not valor:
            continue

        if any(kw in valor for kw in _KW_SERIAL):
            if mapa["serial"] is None:
                mapa["serial"] = idx
        if any(kw in valor for kw in _KW_PRODUCTO):
            if mapa["producto"] is None:
                mapa["producto"] = idx
        if any(kw in valor for kw in _KW_COSTO):
            if mapa["costo"] is None:
                mapa["costo"] = idx
        if any(kw in valor for kw in _KW_CANTIDAD):
            if mapa["cantidad"] is None:
                mapa["cantidad"] = idx
        if any(kw in valor for kw in _KW_BARRAS):
            if mapa["codigo_barras"] is None:
                mapa["codigo_barras"] = idx

    return mapa


def importar_inventario_excel(ruta: Path) -> ResultadoInventario:
    """
    Lee un .xlsx con inventario. Detecta automáticamente la fila de encabezados
    buscando la primera fila que contenga palabras clave de columnas.
    """
    resultado = ResultadoInventario()

    try:
        wb = openpyxl.load_workbook(str(ruta), data_only=True)
    except Exception as exc:
        resultado.errores.append(f"No se pudo abrir el archivo: {exc}")
        return resultado

    ws = wb.active
    if ws.max_row < 2:
        resultado.errores.append("El archivo parece estar vacío.")
        return resultado

    # ── Detectar fila de encabezados (buscar en las primeras 5 filas) ──
    header_row_idx = None
    mapa: dict[str, int | None] = {}

    for row_idx in range(1, min(6, ws.max_row + 1)):
        fila = [ws.cell(row_idx, col).value for col in range(1, ws.max_column + 1)]
        mapa = _detectar_columnas(fila)
        if mapa["producto"] is not None:
            header_row_idx = row_idx
            break

    if header_row_idx is None or mapa["producto"] is None:
        # Sin encabezados detectados — usar posición fija:
        # Col 1=serial, 2=producto, 3=costo, 4=cantidad, 5=barras
        mapa = {"serial": 0, "producto": 1, "costo": 2, "cantidad": 3, "codigo_barras": 4}
        header_row_idx = 1
        resultado.errores.append(
            "No se detectaron encabezados — se usaron las columnas por posición: "
            "1=Serial, 2=Producto, 3=Costo, 4=Cantidad, 5=Código de barras."
        )

    # ── Leer filas de datos ────────────────────────────────────────────
    for row_idx in range(header_row_idx + 1, ws.max_row + 1):
        col_prod = mapa["producto"]
        val_prod = ws.cell(row_idx, col_prod + 1).value if col_prod is not None else None
        if val_prod is None or str(val_prod).strip() == "":
            continue

        resultado.total_leidos += 1
        producto_nombre = str(val_prod).strip()

        def _get(campo: str, default):
            idx = mapa.get(campo)
            if idx is None:
                return default
            return ws.cell(row_idx, idx + 1).value

        # Serial
        serial = str(_get("serial", "") or "").strip()

        # Costo
        try:
            costo = float(_get("costo", 0) or 0)
            if costo < 0:
                costo = 0.0
        except (ValueError, TypeError):
            costo = 0.0

        # Cantidad
        try:
            cantidad = int(float(str(_get("cantidad", 0) or 0).replace(",", ".")))
            if cantidad < 0:
                cantidad = 0
        except (ValueError, TypeError):
            cantidad = 0

        # Código de barras
        cod = str(_get("codigo_barras", "") or "").strip()

        try:
            p = Producto(
                serial=serial,
                producto=producto_nombre,
                costo_unitario=costo,
                cantidad=cantidad,
                codigo_barras=cod,
            )
            resultado.productos.append(p)
        except ValueError as exc:
            resultado.errores.append(f"Fila {row_idx}: {exc} — omitida")

    return resultado
