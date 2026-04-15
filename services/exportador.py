"""
services/exportador.py
Genera archivos .xlsx con los datos de ventas.
Sin dependencias de UI.
"""

from datetime import date
from pathlib import Path

import openpyxl
from openpyxl.styles import (
    Font, PatternFill, Alignment, Border, Side,
)
from openpyxl.utils import get_column_letter

import json

from models.venta import Venta
from models.producto import Producto
from models.factura import Factura
from models.configuracion import Configuracion
from utils.formatters import fecha_corta, nombre_mes


# Paleta de colores
_AZUL_HEADER = "1E3A5F"
_AZUL_SUAVE  = "E8F0FE"
_VERDE       = "D4EDDA"
_ROJO        = "F8D7DA"
_GRIS_FILA   = "F5F5F5"


def _borde_fino() -> Border:
    lado = Side(style="thin", color="CCCCCC")
    return Border(left=lado, right=lado, top=lado, bottom=lado)


# ── Encabezados comunes de ventas ──────────────────────────────────────────
# Col 11 "Pagos JSON" es datos internos — no editar manualmente
_HEADERS_VENTAS = [
    "#", "Fecha", "Producto", "Cant.", "Costo", "Precio venta",
    "Método pago", "Comisión", "Ganancia neta", "Notas", "Pagos JSON"
]

_ANCHOS_VENTAS = [5, 12, 30, 7, 15, 16, 14, 14, 15, 28, 1]

_EJEMPLOS_VENTAS = [
    (1, "04/04/2026", "Casco X-Sport T.M",   1, 85000, 120000, "Efectivo",        0,     35000,  "", ""),
    (2, "04/04/2026", "Aceite 10W-40 1L",    2, 18000,  28000, "Transferencia NEQUI", 0, 20000,  "", ""),
    (3, "04/04/2026", "Guantes cuero talla L", 1, 25000, 40000, "Bold",          2000,   13000,  "Cliente frecuente", ""),
]


def _escribir_encabezados_ventas(ws, titulo_celda: str, titulo_valor: str) -> None:
    """Escribe título (fila 1), fila vacía (2) y encabezados (3) en un worksheet."""
    ws.merge_cells(f"{titulo_celda}:J1")   # solo hasta J — col K es interna
    t = ws[titulo_celda]
    t.value = titulo_valor
    t.font = Font(name="Calibri", bold=True, size=14, color="FFFFFF")
    t.fill = PatternFill("solid", fgColor=_AZUL_HEADER)
    t.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 28

    ws.append([])  # fila 2 vacía

    ws.append(_HEADERS_VENTAS)  # fila 3
    for col_idx in range(1, 12):
        cell = ws.cell(row=3, column=col_idx)
        if col_idx == 11:
            # Columna interna — gris apagada
            cell.font = Font(bold=False, color="AAAAAA", name="Calibri", size=8)
            cell.fill = PatternFill("solid", fgColor="F3F4F6")
        else:
            cell.font = Font(bold=True, color="FFFFFF", name="Calibri", size=10)
            cell.fill = PatternFill("solid", fgColor="2563EB")
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = _borde_fino()
    ws.row_dimensions[3].height = 20


def generar_plantilla_ventas_dia(ruta: Path, fecha: date) -> None:
    """
    Genera un .xlsx vacío con el formato correcto para registrar ventas de un día
    y luego importarlo con ⬆ Importar Excel.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Ventas del Día"

    _escribir_encabezados_ventas(
        ws, "A1",
        f"YJBMOTOCOM — Ventas del {fecha_corta(fecha)}"
    )

    # Filas de ejemplo en gris
    for ej in _EJEMPLOS_VENTAS:
        ws.append(list(ej))
        row = ws.max_row
        for col_idx in range(1, 11):
            c = ws.cell(row=row, column=col_idx)
            c.fill = PatternFill("solid", fgColor="F1F5F9")
            c.font = Font(name="Calibri", size=10, italic=True, color="94A3B8")
            c.border = _borde_fino()
            c.alignment = Alignment(vertical="center")
        ws.row_dimensions[row].height = 18

    # Nota instructiva
    ws.merge_cells(f"A{ws.max_row + 1}:J{ws.max_row + 1}")
    nota = ws.cell(ws.max_row, 1)
    nota.value = (
        "↑ Borra las filas de ejemplo. Agrega tus ventas desde la fila 4. "
        "Si cambias la fecha del título (fila 1), cambia también las fechas de las filas de datos."
    )
    nota.font = Font(name="Calibri", size=9, italic=True, color="6B7280")
    nota.fill = PatternFill("solid", fgColor="FFFBEB")
    nota.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[ws.max_row].height = 24

    for i, ancho in enumerate(_ANCHOS_VENTAS, start=1):
        ws.column_dimensions[get_column_letter(i)].width = ancho

    wb.save(str(ruta))


def generar_plantilla_ventas_mes(ruta: Path, año: int, mes: int,
                                  prestamos: list | None = None) -> None:
    """
    Genera un .xlsx vacío con el formato correcto para registrar ventas de un mes
    y luego importarlo con ⬆ Importar Excel.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = nombre_mes(mes, año)

    _escribir_encabezados_ventas(
        ws, "A1",
        f"YJBMOTOCOM — {nombre_mes(mes, año)}"
    )

    # Filas de ejemplo en gris
    for ej in _EJEMPLOS_VENTAS:
        ws.append(list(ej))
        row = ws.max_row
        for col_idx in range(1, 11):
            c = ws.cell(row=row, column=col_idx)
            c.fill = PatternFill("solid", fgColor="F1F5F9")
            c.font = Font(name="Calibri", size=10, italic=True, color="94A3B8")
            c.border = _borde_fino()
            c.alignment = Alignment(vertical="center")
        ws.row_dimensions[row].height = 18

    # Nota instructiva
    ws.merge_cells(f"A{ws.max_row + 1}:J{ws.max_row + 1}")
    nota = ws.cell(ws.max_row, 1)
    nota.value = (
        "↑ Borra las filas de ejemplo. Agrega tus ventas desde la fila 4. "
        "Puedes incluir ventas de varios días del mes — cada fila tiene su propia fecha."
    )
    nota.font = Font(name="Calibri", size=9, italic=True, color="6B7280")
    nota.fill = PatternFill("solid", fgColor="FFFBEB")
    nota.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[ws.max_row].height = 24

    for i, ancho in enumerate(_ANCHOS_VENTAS, start=1):
        ws.column_dimensions[get_column_letter(i)].width = ancho

    # ── Hoja Préstamos (vacía para que el usuario la llene) ───────────
    ws_prest = wb.create_sheet("Préstamos")
    _escribir_hoja_prestamos(ws_prest, prestamos or [])

    wb.save(str(ruta))


_HEADERS_PRESTAMOS = ["Fecha", "Producto", "Almacén", "Observaciones", "Estado"]
_ANCHOS_PRESTAMOS  = [14, 34, 22, 40, 14]
_ESTADOS_COLOR = {
    "pendiente": "FEF3C7",
    "devuelto":  "D1FAE5",
    "cobrado":   "DBEAFE",
}


def _escribir_hoja_prestamos(ws, prestamos: list) -> None:
    """Escribe título, encabezados y datos de préstamos en el worksheet dado."""
    lado = Side(style="thin", color="CCCCCC")
    borde = Border(left=lado, right=lado, top=lado, bottom=lado)

    # Título
    ws.merge_cells("A1:E1")
    t = ws["A1"]
    t.value = "YJBMOTOCOM — Préstamos"
    t.font = Font(name="Calibri", bold=True, size=13, color="FFFFFF")
    t.fill = PatternFill("solid", fgColor=_AZUL_HEADER)
    t.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 26

    # Encabezados
    ws.append(_HEADERS_PRESTAMOS)
    for col_idx in range(1, 6):
        cell = ws.cell(row=2, column=col_idx)
        cell.font = Font(bold=True, color="FFFFFF", name="Calibri", size=10)
        cell.fill = PatternFill("solid", fgColor="334155")
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = borde
    ws.row_dimensions[2].height = 20

    # Filas de datos (o vacío para plantilla)
    for p in prestamos:
        ws.append([
            p.fecha.strftime("%d/%m/%Y") if hasattr(p.fecha, "strftime") else str(p.fecha),
            p.producto,
            p.almacen,
            p.observaciones or "",
            p.estado,
        ])
        row = ws.max_row
        color = _ESTADOS_COLOR.get(p.estado, "FFFFFF")
        for col_idx in range(1, 6):
            c = ws.cell(row=row, column=col_idx)
            c.fill = PatternFill("solid", fgColor=color)
            c.border = borde
            c.font = Font(name="Calibri", size=10)
            c.alignment = Alignment(vertical="center")
        ws.row_dimensions[row].height = 18

    # Anchos de columna
    for i, ancho in enumerate(_ANCHOS_PRESTAMOS, start=1):
        ws.column_dimensions[get_column_letter(i)].width = ancho


_HEADERS_INVENTARIO = ["Serial", "Producto", "Costo unitario", "Cantidad", "Código barras"]
_ANCHOS_INVENTARIO  = [12, 38, 16, 12, 20]


def _escribir_hoja_inventario(ws, productos: list) -> None:
    """Escribe título, encabezados y datos de inventario en el worksheet dado."""
    lado = Side(style="thin", color="CCCCCC")
    borde = Border(left=lado, right=lado, top=lado, bottom=lado)
    from datetime import date as _date
    hoy = _date.today().strftime("%d/%m/%Y")

    # Título
    ws.merge_cells("A1:E1")
    t = ws["A1"]
    t.value = f"YJBMOTOCOM — Inventario ({hoy})"
    t.font = Font(name="Calibri", bold=True, size=13, color="FFFFFF")
    t.fill = PatternFill("solid", fgColor="0369A1")
    t.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 26

    # Encabezados
    ws.append(_HEADERS_INVENTARIO)
    for col_idx in range(1, 6):
        cell = ws.cell(row=2, column=col_idx)
        cell.font = Font(bold=True, color="FFFFFF", name="Calibri", size=10)
        cell.fill = PatternFill("solid", fgColor="0284C7")
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = borde
    ws.row_dimensions[2].height = 20

    # Datos
    total_referencias  = 0   # líneas con stock > 0
    total_unidades     = 0   # suma de cantidades con stock
    total_valor_inv    = 0.0 # suma de costo_unitario × cantidad (solo stock > 0)
    for i, p in enumerate(productos, start=1):
        ws.append([
            p.serial or "",
            p.producto,
            p.costo_unitario,
            p.cantidad,
            p.codigo_barras or "",
        ])
        row = ws.max_row
        fondo = "F0F9FF" if i % 2 == 0 else "FFFFFF"
        for col_idx in range(1, 6):
            c = ws.cell(row=row, column=col_idx)
            c.fill = PatternFill("solid", fgColor=fondo)
            c.border = borde
            c.font = Font(name="Calibri", size=10)
            c.alignment = Alignment(vertical="center")
        ws.row_dimensions[row].height = 18
        if p.cantidad > 0:
            total_referencias += 1
            total_unidades    += p.cantidad
            total_valor_inv   += p.costo_unitario * p.cantidad

    # ── Fila de totales ───────────────────────────────────────────────────
    ws.append([
        "TOTALES",
        f"{total_referencias} ref. con stock",
        total_valor_inv,   # valor del inventario en col "Costo unitario"
        total_unidades,    # unidades totales en stock en col "Cantidad"
        "",
    ])
    total_row = ws.max_row
    for col_idx in range(1, 6):
        c = ws.cell(row=total_row, column=col_idx)
        c.font = Font(bold=True, name="Calibri", size=10)
        c.fill = PatternFill("solid", fgColor="E0F2FE")
        c.border = borde
        c.alignment = Alignment(vertical="center")
    ws.row_dimensions[total_row].height = 20

    # Anchos
    for i, ancho in enumerate(_ANCHOS_INVENTARIO, start=1):
        ws.column_dimensions[get_column_letter(i)].width = ancho


_HEADERS_FACTURAS = ["Descripción", "Proveedor", "Monto", "Fecha llegada", "Fecha vencimiento", "Estado", "Notas"]
_ANCHOS_FACTURAS  = [38, 24, 16, 14, 16, 12, 34]
_FACTURA_ESTADO_COLOR = {
    "pendiente": "FEF3C7",
    "pagada":    "DCFCE7",
}


def _escribir_hoja_facturas(ws, facturas: list) -> None:
    """Escribe título, encabezados y datos de facturas en el worksheet dado."""
    lado = Side(style="thin", color="CCCCCC")
    borde = Border(left=lado, right=lado, top=lado, bottom=lado)
    ncols = len(_HEADERS_FACTURAS)

    # Título
    ws.merge_cells(f"A1:{get_column_letter(ncols)}1")
    t = ws["A1"]
    t.value = "YJBMOTOCOM — Facturas y Recibos"
    t.font = Font(name="Calibri", bold=True, size=13, color="FFFFFF")
    t.fill = PatternFill("solid", fgColor="92400E")
    t.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 26

    # Encabezados
    ws.append(_HEADERS_FACTURAS)
    for col_idx in range(1, ncols + 1):
        cell = ws.cell(row=2, column=col_idx)
        cell.font = Font(bold=True, color="FFFFFF", name="Calibri", size=10)
        cell.fill = PatternFill("solid", fgColor="B45309")
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = borde
    ws.row_dimensions[2].height = 20

    # Datos
    for i, f in enumerate(facturas, start=1):
        fecha_str = (
            f.fecha_llegada.strftime("%d/%m/%Y")
            if hasattr(f.fecha_llegada, "strftime")
            else str(f.fecha_llegada)
        )
        fv = getattr(f, "fecha_vencimiento", None)
        fv_str = fv.strftime("%d/%m/%Y") if fv else ""
        ws.append([
            f.descripcion,
            f.proveedor,
            f.monto,
            fecha_str,
            fv_str,
            f.estado,
            f.notas or "",
        ])
        row = ws.max_row
        color = _FACTURA_ESTADO_COLOR.get(f.estado, "FFFFFF")
        for col_idx in range(1, ncols + 1):
            c = ws.cell(row=row, column=col_idx)
            c.fill = PatternFill("solid", fgColor=color)
            c.border = borde
            c.font = Font(name="Calibri", size=10)
            c.alignment = Alignment(vertical="center")
        ws.row_dimensions[row].height = 18

    # Anchos
    for i, ancho in enumerate(_ANCHOS_FACTURAS, start=1):
        ws.column_dimensions[get_column_letter(i)].width = ancho


_HEADERS_GASTOS = ["Fecha", "Descripción", "Monto", "Categoría"]
_ANCHOS_GASTOS  = [14, 40, 16, 14]


def _escribir_hoja_gastos(ws, gastos: list) -> None:
    """Escribe título, encabezados y datos de gastos diarios."""
    lado = Side(style="thin", color="CCCCCC")
    borde = Border(left=lado, right=lado, top=lado, bottom=lado)

    ws.merge_cells("A1:D1")
    t = ws["A1"]
    t.value = "YJBMOTOCOM — Gastos Operativos Diarios"
    t.font = Font(name="Calibri", bold=True, size=13, color="FFFFFF")
    t.fill = PatternFill("solid", fgColor="6D28D9")
    t.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 26

    ws.append(_HEADERS_GASTOS)
    for col_idx in range(1, 5):
        cell = ws.cell(row=2, column=col_idx)
        cell.font = Font(bold=True, color="FFFFFF", name="Calibri", size=10)
        cell.fill = PatternFill("solid", fgColor="7C3AED")
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = borde
    ws.row_dimensions[2].height = 20

    for i, g in enumerate(gastos, start=1):
        fecha_str = (
            g.fecha.strftime("%d/%m/%Y")
            if hasattr(g.fecha, "strftime")
            else str(g.fecha)
        )
        cat = getattr(g, "categoria", "Otro") or "Otro"
        ws.append([fecha_str, g.descripcion, g.monto, cat])
        row = ws.max_row
        fondo = "F5F3FF" if i % 2 == 0 else "FFFFFF"
        for col_idx in range(1, 5):
            c = ws.cell(row=row, column=col_idx)
            c.fill = PatternFill("solid", fgColor=fondo)
            c.border = borde
            c.font = Font(name="Calibri", size=10)
            c.alignment = Alignment(vertical="center")
        ws.row_dimensions[row].height = 18

    for i, ancho in enumerate(_ANCHOS_GASTOS, start=1):
        ws.column_dimensions[get_column_letter(i)].width = ancho


_HEADERS_CONFIG = [
    "Arriendo", "Sueldo", "Servicios", "Otros gastos",
    "Días mes", "Comisión Bold (%)", "Comisión Addi (%)", "Comisión Transf. (%)"
]
_ANCHOS_CONFIG = [16, 16, 16, 16, 11, 18, 18, 20]


def _escribir_hoja_configuracion(ws, cfg) -> None:
    """Escribe título, encabezados y fila única de configuración."""
    lado = Side(style="thin", color="CCCCCC")
    borde = Border(left=lado, right=lado, top=lado, bottom=lado)
    ncols = len(_HEADERS_CONFIG)

    ws.merge_cells(f"A1:{get_column_letter(ncols)}1")
    t = ws["A1"]
    t.value = "YJBMOTOCOM — Configuración"
    t.font = Font(name="Calibri", bold=True, size=13, color="FFFFFF")
    t.fill = PatternFill("solid", fgColor="065F46")
    t.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 26

    ws.append(_HEADERS_CONFIG)
    for col_idx in range(1, ncols + 1):
        cell = ws.cell(row=2, column=col_idx)
        cell.font = Font(bold=True, color="FFFFFF", name="Calibri", size=10)
        cell.fill = PatternFill("solid", fgColor="047857")
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = borde
    ws.row_dimensions[2].height = 20

    if cfg is None:
        valores = [0, 0, 0, 0, 30, 0, 0, 0]
    else:
        valores = [
            cfg.arriendo, cfg.sueldo, cfg.servicios, cfg.otros_gastos,
            cfg.dias_mes, cfg.comision_bold, cfg.comision_addi, cfg.comision_transferencia,
        ]
    ws.append(valores)
    row = ws.max_row
    for col_idx in range(1, ncols + 1):
        c = ws.cell(row=row, column=col_idx)
        c.fill = PatternFill("solid", fgColor="ECFDF5")
        c.border = borde
        c.font = Font(name="Calibri", size=10, bold=True)
        c.alignment = Alignment(horizontal="right", vertical="center")
    ws.row_dimensions[row].height = 22

    for i, ancho in enumerate(_ANCHOS_CONFIG, start=1):
        ws.column_dimensions[get_column_letter(i)].width = ancho


def exportar_todo(
    ruta: Path,
    ventas: list | None = None,
    prestamos: list | None = None,
    productos: list | None = None,
    facturas: list | None = None,
    gastos: list | None = None,
    configuracion=None,
) -> None:
    """
    Genera un .xlsx con las hojas que se pasen (None = omitir esa hoja).
    Hojas disponibles: Ventas | Préstamos | Inventario | Facturas | Gastos | Configuración
    """
    wb = openpyxl.Workbook()
    primera_hoja_usada = False

    def _hoja(titulo_hoja: str) -> object:
        """Crea o reutiliza la hoja activa (la primera se crea automáticamente)."""
        nonlocal primera_hoja_usada
        if not primera_hoja_usada:
            ws = wb.active
            ws.title = titulo_hoja
            primera_hoja_usada = True
        else:
            ws = wb.create_sheet(titulo_hoja)
        return ws

    # ── Hoja Ventas (opcional) ────────────────────────────────────────────
    if ventas is not None:
        ws_v = _hoja("Ventas")
        ws_v.merge_cells("A1:J1")
        titulo_c = ws_v["A1"]
        titulo_c.value = "YJBMOTOCOM — Historial de Ventas"
        titulo_c.font = Font(name="Calibri", bold=True, size=14, color="FFFFFF")
        titulo_c.fill = PatternFill("solid", fgColor=_AZUL_HEADER)
        titulo_c.alignment = Alignment(horizontal="center", vertical="center")
        ws_v.row_dimensions[1].height = 28

        ws_v.append([])
        ws_v.append(_HEADERS_VENTAS)
        for col_idx in range(1, 12):
            cell = ws_v.cell(row=3, column=col_idx)
            if col_idx == 11:
                cell.font = Font(bold=False, color="AAAAAA", name="Calibri", size=8)
                cell.fill = PatternFill("solid", fgColor="F3F4F6")
            else:
                cell.font = Font(bold=True, color="FFFFFF", name="Calibri", size=10)
                cell.fill = PatternFill("solid", fgColor="2563EB")
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = _borde_fino()
        ws_v.row_dimensions[3].height = 20

        total_cant    = 0
        total_costos  = 0.0
        total_ingresos = 0.0
        total_comision = 0.0
        total_neta    = 0.0
        for i, v in enumerate(ventas, start=1):
            pagos_json = json.dumps(v.pagos_combinados, ensure_ascii=False) if v.pagos_combinados else ""
            ws_v.append([
                i, fecha_corta(v.fecha), v.producto, v.cantidad,
                v.costo, v.precio, v.metodo_pago,
                v.comision, v.ganancia_neta, v.notas, pagos_json,
            ])
            row = ws_v.max_row
            fondo = _GRIS_FILA if i % 2 == 0 else "FFFFFF"
            for col_idx in range(1, 12):
                c = ws_v.cell(row=row, column=col_idx)
                if col_idx == 11:
                    c.fill = PatternFill("solid", fgColor="F9FAFB")
                    c.font = Font(name="Calibri", size=8, color="AAAAAA")
                else:
                    c.fill = PatternFill("solid", fgColor=fondo)
                    c.font = Font(name="Calibri", size=10)
                c.border = _borde_fino()
            cell_neta = ws_v.cell(row=row, column=9)
            cell_neta.fill = PatternFill(
                "solid", fgColor=_VERDE if v.ganancia_neta >= 0 else _ROJO
            )
            total_cant     += v.cantidad
            total_costos   += v.costo * v.cantidad
            total_ingresos += v.precio * v.cantidad
            total_comision += v.comision
            total_neta     += v.ganancia_neta

        # ── Fila de totales ───────────────────────────────────────────────
        ws_v.append([
            "", "TOTALES",
            f"{len(ventas)} venta(s)",
            total_cant,          # Cant.
            total_costos,        # Costo total
            total_ingresos,      # Ingresos totales
            "",                  # Método pago
            total_comision,      # Comisión total
            total_neta,          # Ganancia neta total
            "", "",
        ])
        total_row = ws_v.max_row
        for col_idx in range(1, 12):
            c = ws_v.cell(row=total_row, column=col_idx)
            c.font = Font(bold=True, name="Calibri", size=10)
            c.fill = PatternFill("solid", fgColor=_AZUL_SUAVE)
            c.border = _borde_fino()
        # Colorear celda de ganancia neta total
        ws_v.cell(row=total_row, column=9).fill = PatternFill(
            "solid", fgColor=_VERDE if total_neta >= 0 else _ROJO
        )

        for i, ancho in enumerate(_ANCHOS_VENTAS, start=1):
            ws_v.column_dimensions[get_column_letter(i)].width = ancho
        ws_v.column_dimensions["K"].width = 1

    # ── Hoja Préstamos (opcional) ─────────────────────────────────────────
    if prestamos is not None:
        _escribir_hoja_prestamos(_hoja("Préstamos"), prestamos)

    # ── Hoja Inventario (opcional) ────────────────────────────────────────
    if productos is not None:
        _escribir_hoja_inventario(_hoja("Inventario"), productos)

    # ── Hoja Facturas (opcional) ──────────────────────────────────────────
    if facturas is not None:
        _escribir_hoja_facturas(_hoja("Facturas"), facturas)

    # ── Hoja Gastos (opcional) ────────────────────────────────────────────
    if gastos is not None:
        _escribir_hoja_gastos(_hoja("Gastos"), gastos)

    # ── Hoja Configuración (opcional) ─────────────────────────────────────
    if configuracion is not None:
        _escribir_hoja_configuracion(_hoja("Configuración"), configuracion)

    # Si ninguna hoja fue incluida, agregar una de aviso
    if not primera_hoja_usada:
        wb.active.title = "Sin datos"
        wb.active["A1"] = "No se seleccionó ninguna hoja para exportar."

    wb.save(str(ruta))


def generar_plantilla_todo(ruta: Path) -> None:
    """
    Genera un .xlsx vacío con las tres hojas (Ventas, Préstamos, Inventario)
    listo para ser rellenado por el usuario e importado desde el panel
    Exportar / Importar.
    Incluye filas de ejemplo en gris para guiar el formato.
    """
    wb = openpyxl.Workbook()

    # ── Hoja Ventas ───────────────────────────────────────────────────────
    ws_v = wb.active
    ws_v.title = "Ventas"
    _escribir_encabezados_ventas(ws_v, "A1", "YJBMOTOCOM — Historial de Ventas")

    for ej in _EJEMPLOS_VENTAS:
        ws_v.append(list(ej))
        row = ws_v.max_row
        for col_idx in range(1, 11):
            c = ws_v.cell(row=row, column=col_idx)
            c.fill = PatternFill("solid", fgColor="F1F5F9")
            c.font = Font(name="Calibri", size=10, italic=True, color="94A3B8")
            c.border = _borde_fino()
            c.alignment = Alignment(vertical="center")
        ws_v.row_dimensions[row].height = 18

    ws_v.merge_cells(f"A{ws_v.max_row + 1}:J{ws_v.max_row + 1}")
    nota_v = ws_v.cell(ws_v.max_row, 1)
    nota_v.value = (
        "↑ Borra las filas de ejemplo. Agrega tus ventas desde la fila 4. "
        "Puedes incluir ventas de cualquier mes y año — cada fila tiene su propia fecha."
    )
    nota_v.font = Font(name="Calibri", size=9, italic=True, color="6B7280")
    nota_v.fill = PatternFill("solid", fgColor="FFFBEB")
    nota_v.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws_v.row_dimensions[ws_v.max_row].height = 24
    for i, ancho in enumerate(_ANCHOS_VENTAS, start=1):
        ws_v.column_dimensions[get_column_letter(i)].width = ancho

    # ── Hoja Préstamos ────────────────────────────────────────────────────
    ws_p = wb.create_sheet("Préstamos")
    _escribir_hoja_prestamos(ws_p, [])   # vacía con encabezados y formato

    lado = Side(style="thin", color="CCCCCC")
    borde = Border(left=lado, right=lado, top=lado, bottom=lado)
    _EJEMPLOS_PRESTAMOS = [
        ("15/04/2026", "Casco X-Sport Rojo T.M", "Almacén Norte", "Para revisión", "pendiente"),
        ("20/04/2026", "Guantes cuero talla L",  "Almacén Sur",   "",              "devuelto"),
    ]
    for ej in _EJEMPLOS_PRESTAMOS:
        ws_p.append(list(ej))
        row = ws_p.max_row
        for col_idx in range(1, 6):
            c = ws_p.cell(row=row, column=col_idx)
            c.fill = PatternFill("solid", fgColor="F1F5F9")
            c.font = Font(name="Calibri", size=10, italic=True, color="94A3B8")
            c.border = borde
            c.alignment = Alignment(vertical="center")
        ws_p.row_dimensions[row].height = 18

    ws_p.merge_cells(f"A{ws_p.max_row + 1}:E{ws_p.max_row + 1}")
    nota_p = ws_p.cell(ws_p.max_row, 1)
    nota_p.value = "↑ Borra los ejemplos. Estados válidos: pendiente | devuelto | cobrado"
    nota_p.font = Font(name="Calibri", size=9, italic=True, color="6B7280")
    nota_p.fill = PatternFill("solid", fgColor="FFFBEB")
    nota_p.alignment = Alignment(horizontal="center", vertical="center")
    ws_p.row_dimensions[ws_p.max_row].height = 20

    # ── Hoja Inventario ───────────────────────────────────────────────────
    ws_i = wb.create_sheet("Inventario")
    _escribir_hoja_inventario(ws_i, [])   # vacía con encabezados y formato

    _EJEMPLOS_INV = [
        ("001", "Casco X-Sport Rojo T.M",  85000, 5,  "7709001234567"),
        ("002", "Aceite 10W-40 1 litro",   18000, 12, ""),
        ("003", "Guantes cuero talla L",   25000, 8,  "7709009876543"),
    ]
    lado2 = Side(style="thin", color="CCCCCC")
    borde2 = Border(left=lado2, right=lado2, top=lado2, bottom=lado2)
    for ej in _EJEMPLOS_INV:
        ws_i.append(list(ej))
        row = ws_i.max_row
        for col_idx in range(1, 6):
            c = ws_i.cell(row=row, column=col_idx)
            c.fill = PatternFill("solid", fgColor="F1F5F9")
            c.font = Font(name="Calibri", size=10, italic=True, color="94A3B8")
            c.border = borde2
            c.alignment = Alignment(vertical="center")
        ws_i.row_dimensions[row].height = 18

    ws_i.merge_cells(f"A{ws_i.max_row + 1}:E{ws_i.max_row + 1}")
    nota_i = ws_i.cell(ws_i.max_row, 1)
    nota_i.value = "↑ Borra los ejemplos. Agrega tus productos desde la fila 3."
    nota_i.font = Font(name="Calibri", size=9, italic=True, color="6B7280")
    nota_i.fill = PatternFill("solid", fgColor="FFFBEB")
    nota_i.alignment = Alignment(horizontal="center", vertical="center")
    ws_i.row_dimensions[ws_i.max_row].height = 20

    # ── Hoja Facturas ─────────────────────────────────────────────────────
    ws_f = wb.create_sheet("Facturas")
    _escribir_hoja_facturas(ws_f, [])   # vacía con encabezados y formato

    _EJEMPLOS_FACT = [
        ("Arriendo local",         "Propietario Norte", 1500000, "01/04/2026", "pendiente", ""),
        ("Proveedor cascos Bogotá", "MotoPartes S.A.S", 850000,  "10/04/2026", "pendiente", "Factura #2341"),
        ("Servicios públicos",      "EPM",               95000,   "05/04/2026", "pagada",    "Pagada el 08/04"),
    ]
    lado3 = Side(style="thin", color="CCCCCC")
    borde3 = Border(left=lado3, right=lado3, top=lado3, bottom=lado3)
    for ej in _EJEMPLOS_FACT:
        ws_f.append(list(ej))
        row = ws_f.max_row
        for col_idx in range(1, 7):
            c = ws_f.cell(row=row, column=col_idx)
            c.fill = PatternFill("solid", fgColor="F1F5F9")
            c.font = Font(name="Calibri", size=10, italic=True, color="94A3B8")
            c.border = borde3
            c.alignment = Alignment(vertical="center")
        ws_f.row_dimensions[row].height = 18

    ws_f.merge_cells(f"A{ws_f.max_row + 1}:F{ws_f.max_row + 1}")
    nota_f = ws_f.cell(ws_f.max_row, 1)
    nota_f.value = "↑ Borra los ejemplos. Estados válidos: pendiente | pagada"
    nota_f.font = Font(name="Calibri", size=9, italic=True, color="6B7280")
    nota_f.fill = PatternFill("solid", fgColor="FFFBEB")
    nota_f.alignment = Alignment(horizontal="center", vertical="center")
    ws_f.row_dimensions[ws_f.max_row].height = 20

    # ── Hoja Gastos ───────────────────────────────────────────────────────
    ws_g = wb.create_sheet("Gastos")
    _escribir_hoja_gastos(ws_g, [])

    lado4 = Side(style="thin", color="CCCCCC")
    borde4 = Border(left=lado4, right=lado4, top=lado4, bottom=lado4)
    _EJEMPLOS_GASTOS = [
        ("01/04/2026", "Transporte moto",        25000),
        ("01/04/2026", "Almuerzo",                15000),
        ("02/04/2026", "Insumos limpieza local",  12000),
    ]
    for ej in _EJEMPLOS_GASTOS:
        ws_g.append(list(ej))
        row = ws_g.max_row
        for col_idx in range(1, 4):
            c = ws_g.cell(row=row, column=col_idx)
            c.fill = PatternFill("solid", fgColor="F1F5F9")
            c.font = Font(name="Calibri", size=10, italic=True, color="94A3B8")
            c.border = borde4
            c.alignment = Alignment(vertical="center")
        ws_g.row_dimensions[row].height = 18

    ws_g.merge_cells(f"A{ws_g.max_row + 1}:C{ws_g.max_row + 1}")
    nota_g = ws_g.cell(ws_g.max_row, 1)
    nota_g.value = "↑ Borra los ejemplos. Agrega tus gastos diarios desde la fila 3."
    nota_g.font = Font(name="Calibri", size=9, italic=True, color="6B7280")
    nota_g.fill = PatternFill("solid", fgColor="FFFBEB")
    nota_g.alignment = Alignment(horizontal="center", vertical="center")
    ws_g.row_dimensions[ws_g.max_row].height = 20

    # ── Hoja Configuración (con valores por defecto del negocio) ─────��────
    ws_c = wb.create_sheet("Configuración")
    cfg_defecto = Configuracion(
        arriendo=3_000_000,
        sueldo=2_000_000,
        servicios=300_000,
        otros_gastos=0,
        dias_mes=30,
        comision_bold=0,
        comision_addi=0,
        comision_transferencia=0,
    )
    _escribir_hoja_configuracion(ws_c, cfg_defecto)

    ws_c.merge_cells(f"A{ws_c.max_row + 1}:{get_column_letter(len(_HEADERS_CONFIG))}{ws_c.max_row + 1}")
    nota_c = ws_c.cell(ws_c.max_row, 1)
    nota_c.value = (
        "Edita los valores de la fila 3. "
        "Las comisiones son porcentajes (ej: 3.49 para 3.49%)."
    )
    nota_c.font = Font(name="Calibri", size=9, italic=True, color="6B7280")
    nota_c.fill = PatternFill("solid", fgColor="FFFBEB")
    nota_c.alignment = Alignment(horizontal="center", vertical="center")
    ws_c.row_dimensions[ws_c.max_row].height = 20

    wb.save(str(ruta))


def exportar_ventas_dia(ventas: list[Venta], fecha: date, ruta: Path) -> None:
    """
    Genera un .xlsx con todas las ventas de un día.
    Incluye fila de totales al final.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Ventas del Día"

    # ---- Título ----
    ws.merge_cells("A1:J1")
    titulo = ws["A1"]
    titulo.value = f"YJBMOTOCOM — Ventas del {fecha_corta(fecha)}"
    titulo.font = Font(name="Calibri", bold=True, size=14, color="FFFFFF")
    titulo.fill = PatternFill("solid", fgColor=_AZUL_HEADER)
    titulo.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 28

    # ---- Encabezados ----
    headers = [
        "#", "Fecha", "Producto", "Cant.", "Costo", "Precio venta",
        "Método pago", "Comisión", "Ganancia neta", "Notas"
    ]
    ws.append([])           # fila 2 vacía
    ws.append(headers)      # fila 3
    for col_idx, _ in enumerate(headers, start=1):
        cell = ws.cell(row=3, column=col_idx)
        cell.font = Font(bold=True, color="FFFFFF", name="Calibri", size=10)
        cell.fill = PatternFill("solid", fgColor="2563EB")
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = _borde_fino()
    ws.row_dimensions[3].height = 20

    # ---- Datos ----
    total_ingresos = total_costos = total_comision = total_neta = 0.0
    for i, v in enumerate(ventas, start=1):
        fila = [
            i,
            fecha_corta(v.fecha),
            v.producto,
            v.cantidad,
            v.costo,
            v.precio,
            v.metodo_pago,
            v.comision,
            v.ganancia_neta,
            v.notas,
        ]
        ws.append(fila)
        row = ws.max_row
        fondo = _GRIS_FILA if i % 2 == 0 else "FFFFFF"
        for col_idx in range(1, 11):
            c = ws.cell(row=row, column=col_idx)
            c.fill = PatternFill("solid", fgColor=fondo)
            c.border = _borde_fino()
            c.font = Font(name="Calibri", size=10)
            c.alignment = Alignment(vertical="center")
        # Números a la derecha
        for col_idx in (4, 5, 6, 8, 9):
            ws.cell(row=row, column=col_idx).alignment = Alignment(
                horizontal="right", vertical="center"
            )
        # Color ganancia neta
        cell_neta = ws.cell(row=row, column=9)
        if v.ganancia_neta >= 0:
            cell_neta.fill = PatternFill("solid", fgColor=_VERDE)
        else:
            cell_neta.fill = PatternFill("solid", fgColor=_ROJO)

        total_ingresos += v.precio * v.cantidad
        total_costos += v.costo * v.cantidad
        total_comision += v.comision
        total_neta += v.ganancia_neta

    # ---- Fila totales ----
    ws.append([
        "", "TOTALES", f"{len(ventas)} venta(s)", "",
        total_costos, total_ingresos, "",
        total_comision, total_neta, ""
    ])
    total_row = ws.max_row
    for col_idx in range(1, 11):
        c = ws.cell(row=total_row, column=col_idx)
        c.font = Font(bold=True, name="Calibri", size=10)
        c.fill = PatternFill("solid", fgColor=_AZUL_SUAVE)
        c.border = _borde_fino()
    ws.row_dimensions[total_row].height = 18

    # ---- Anchos de columna ----
    anchos = [5, 12, 30, 7, 15, 16, 14, 14, 15, 28]
    for i, ancho in enumerate(anchos, start=1):
        ws.column_dimensions[get_column_letter(i)].width = ancho

    wb.save(str(ruta))


def exportar_ventas_mes(ventas: list[Venta], año: int, mes: int, ruta: Path,
                        prestamos: list | None = None) -> None:
    """
    Genera un .xlsx con todas las ventas de un mes.
    Si se pasan préstamos, agrega una segunda hoja «Préstamos».
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = nombre_mes(mes, año)

    ws.merge_cells("A1:J1")
    titulo = ws["A1"]
    titulo.value = f"YJBMOTOCOM — {nombre_mes(mes, año)}"
    titulo.font = Font(name="Calibri", bold=True, size=14, color="FFFFFF")
    titulo.fill = PatternFill("solid", fgColor=_AZUL_HEADER)
    titulo.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 28

    headers = [
        "#", "Fecha", "Producto", "Cant.", "Costo", "Precio venta",
        "Método pago", "Comisión", "Ganancia neta", "Notas"
    ]
    ws.append([])
    ws.append(headers)
    for col_idx in range(1, 11):
        cell = ws.cell(row=3, column=col_idx)
        cell.font = Font(bold=True, color="FFFFFF", name="Calibri", size=10)
        cell.fill = PatternFill("solid", fgColor="2563EB")
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = _borde_fino()

    total_neta = 0.0
    for i, v in enumerate(ventas, start=1):
        ws.append([
            i, fecha_corta(v.fecha), v.producto, v.cantidad,
            v.costo, v.precio, v.metodo_pago,
            v.comision, v.ganancia_neta, v.notas,
        ])
        row = ws.max_row
        fondo = _GRIS_FILA if i % 2 == 0 else "FFFFFF"
        for col_idx in range(1, 11):
            c = ws.cell(row=row, column=col_idx)
            c.fill = PatternFill("solid", fgColor=fondo)
            c.border = _borde_fino()
            c.font = Font(name="Calibri", size=10)
        cell_neta = ws.cell(row=row, column=9)
        if v.ganancia_neta >= 0:
            cell_neta.fill = PatternFill("solid", fgColor=_VERDE)
        else:
            cell_neta.fill = PatternFill("solid", fgColor=_ROJO)
        total_neta += v.ganancia_neta

    ws.append(["", "TOTALES", f"{len(ventas)} venta(s)", "", "", "", "", "", total_neta, ""])
    total_row = ws.max_row
    for col_idx in range(1, 11):
        c = ws.cell(row=total_row, column=col_idx)
        c.font = Font(bold=True, name="Calibri", size=10)
        c.fill = PatternFill("solid", fgColor=_AZUL_SUAVE)
        c.border = _borde_fino()

    anchos = [5, 12, 30, 7, 15, 16, 14, 14, 15, 28]
    for i, ancho in enumerate(anchos, start=1):
        ws.column_dimensions[get_column_letter(i)].width = ancho

    # ── Hoja Préstamos ────────────────────────────────────────────────────
    if prestamos is not None:
        ws_prest = wb.create_sheet("Préstamos")
        _escribir_hoja_prestamos(ws_prest, prestamos)

    wb.save(str(ruta))
