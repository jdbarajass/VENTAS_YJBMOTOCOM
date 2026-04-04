"""
services/exportador.py
Genera archivos .xlsx con los datos de ventas.
Sin dependencias de UI.
"""

from datetime import date
from pathlib import Path

import openpyxl
from openpyxl.styles import (
    Font, PatternFill, Alignment, Border, Side, numbers
)
from openpyxl.utils import get_column_letter

from models.venta import Venta
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


def exportar_ventas_mes(ventas: list[Venta], año: int, mes: int, ruta: Path) -> None:
    """
    Genera un .xlsx con todas las ventas de un mes, agrupadas por día.
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

    wb.save(str(ruta))
