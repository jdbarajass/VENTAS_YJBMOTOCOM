"""
services/importador.py
Importa ventas desde un archivo .xlsx exportado por YJBMOTOCOM.
Sin dependencias de UI.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Literal

import openpyxl

from models.venta import Venta
from utils.formatters import MESES_ES, nombre_mes


# Lookup inverso: "enero" -> 1
_MES_NUM: dict[str, int] = {v.lower(): k for k, v in MESES_ES.items()}


@dataclass
class ResultadoImportacion:
    ventas: list[Venta] = field(default_factory=list)
    tipo: Literal["dia", "mes"] = "dia"
    fecha: date | None = None       # tipo "dia"
    año: int | None = None          # tipo "mes"
    mes: int | None = None          # tipo "mes"
    errores: list[str] = field(default_factory=list)

    @property
    def periodo_str(self) -> str:
        if self.tipo == "dia" and self.fecha:
            return self.fecha.strftime("%d/%m/%Y")
        if self.tipo == "mes" and self.año and self.mes:
            return nombre_mes(self.mes, self.año)
        return "período desconocido"


def importar_desde_excel(ruta: Path) -> ResultadoImportacion:
    """
    Lee un .xlsx exportado por YJBMOTOCOM y retorna las ventas parseadas.
    Detecta automáticamente si es diario o mensual por el título (fila 1).

    Formato esperado:
      Fila 1 : título  "YJBMOTOCOM — Ventas del DD/MM/YYYY"  (dia)
               o       "YJBMOTOCOM — Mes YYYY"               (mes)
      Fila 2 : vacía
      Fila 3 : encabezados
      Fila 4+: datos
      Última : fila TOTALES
    """
    resultado = ResultadoImportacion()

    try:
        wb = openpyxl.load_workbook(str(ruta), data_only=True)
    except Exception as exc:
        resultado.errores.append(f"No se pudo abrir el archivo: {exc}")
        return resultado

    ws = wb.active

    # ── Detectar período desde el título ──────────────────────────────
    titulo = str(ws.cell(1, 1).value or "")

    if "Ventas del" in titulo:
        resultado.tipo = "dia"
        parte = titulo.split("Ventas del")[-1].strip()
        try:
            resultado.fecha = datetime.strptime(parte, "%d/%m/%Y").date()
        except ValueError:
            resultado.errores.append(
                f"No se pudo leer la fecha del título: '{titulo}'"
            )
    else:
        resultado.tipo = "mes"
        # "YJBMOTOCOM — Abril 2026"
        parte = titulo.split("—")[-1].strip()
        partes = parte.split()
        if len(partes) >= 2:
            resultado.mes = _MES_NUM.get(partes[0].lower())
            try:
                resultado.año = int(partes[1])
            except ValueError:
                pass
        if not resultado.mes or not resultado.año:
            resultado.errores.append(
                f"No se pudo leer el mes del título: '{titulo}'"
            )

    # ── Leer filas de datos (desde fila 4) ───────────────────────────
    for row_idx in range(4, ws.max_row + 1):
        col2 = ws.cell(row_idx, 2).value

        # Fila vacía: continuar
        if col2 is None:
            continue

        # Fila TOTALES: detener
        if str(col2).upper().strip() == "TOTALES":
            break

        # ── Fecha ──
        try:
            if isinstance(col2, date):
                venta_fecha = col2
            else:
                venta_fecha = datetime.strptime(str(col2).strip(), "%d/%m/%Y").date()
        except (ValueError, TypeError):
            resultado.errores.append(
                f"Fila {row_idx}: fecha inválida '{col2}' — omitida"
            )
            continue

        # ── Producto ──
        producto = str(ws.cell(row_idx, 3).value or "").strip()
        if not producto:
            resultado.errores.append(f"Fila {row_idx}: producto vacío — omitida")
            continue

        # ── Cantidad ──
        try:
            cantidad = int(ws.cell(row_idx, 4).value or 1)
            if cantidad < 1:
                cantidad = 1
        except (ValueError, TypeError):
            cantidad = 1

        # ── Costo ──
        try:
            costo = float(ws.cell(row_idx, 5).value or 0)
            if costo < 0:
                costo = 0.0
        except (ValueError, TypeError):
            costo = 0.0

        # ── Precio venta ──
        try:
            precio = float(ws.cell(row_idx, 6).value or 0)
            if precio < 0:
                precio = 0.0
        except (ValueError, TypeError):
            precio = 0.0

        # ── Método de pago ──
        metodo_pago = str(ws.cell(row_idx, 7).value or "Efectivo").strip() or "Efectivo"

        # ── Comisión (total, no unitaria) ──
        try:
            comision = float(ws.cell(row_idx, 8).value or 0)
            if comision < 0:
                comision = 0.0
        except (ValueError, TypeError):
            comision = 0.0

        # ── Ganancia neta (total) ──
        try:
            ganancia_neta = float(ws.cell(row_idx, 9).value or 0)
        except (ValueError, TypeError):
            ganancia_neta = 0.0

        # ── Notas ──
        notas = str(ws.cell(row_idx, 10).value or "").strip()

        try:
            v = Venta(
                producto=producto,
                costo=costo,
                precio=precio,
                metodo_pago=metodo_pago,
                cantidad=cantidad,
                comision=comision,
                ganancia_neta=ganancia_neta,
                notas=notas,
                fecha=venta_fecha,
            )
            resultado.ventas.append(v)
        except ValueError as exc:
            resultado.errores.append(f"Fila {row_idx}: {exc} — omitida")

    return resultado
