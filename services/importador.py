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
from models.prestamo import Prestamo
from models.producto import Producto
from utils.formatters import MESES_ES, nombre_mes


# Lookup inverso: "enero" -> 1
_MES_NUM: dict[str, int] = {v.lower(): k for k, v in MESES_ES.items()}


@dataclass
class ResultadoImportacion:
    ventas: list[Venta] = field(default_factory=list)
    prestamos: list[Prestamo] = field(default_factory=list)
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


def _leer_prestamos(ws) -> list[Prestamo]:
    """
    Lee la hoja «Préstamos» generada por YJBMOTOCOM.
    Espera: fila 1 = título, fila 2 = encabezados, fila 3+ = datos.
    Columnas: Fecha | Producto | Almacén | Observaciones | Estado
    """
    prestamos: list[Prestamo] = []
    for row_idx in range(3, ws.max_row + 1):
        producto = str(ws.cell(row_idx, 2).value or "").strip()
        if not producto:
            continue
        almacen = str(ws.cell(row_idx, 3).value or "").strip()
        if not almacen:
            continue

        # Fecha — openpyxl puede devolver datetime (subclase de date)
        fecha_val = ws.cell(row_idx, 1).value
        try:
            if isinstance(fecha_val, datetime):
                p_fecha = fecha_val.date()
            elif isinstance(fecha_val, date):
                p_fecha = fecha_val
            else:
                p_fecha = datetime.strptime(str(fecha_val).strip(), "%d/%m/%Y").date()
        except (ValueError, TypeError):
            p_fecha = date.today()

        observaciones = str(ws.cell(row_idx, 4).value or "").strip()
        estado_raw = str(ws.cell(row_idx, 5).value or "pendiente").strip().lower()
        if estado_raw not in ("pendiente", "devuelto", "cobrado"):
            estado_raw = "pendiente"

        try:
            prestamos.append(Prestamo(
                producto=producto,
                almacen=almacen,
                fecha=p_fecha,
                observaciones=observaciones,
                estado=estado_raw,
            ))
        except ValueError:
            pass
    return prestamos


@dataclass
class ResultadoImportacionTotal:
    ventas: list[Venta] = field(default_factory=list)
    año: int | None = None
    mes: int | None = None
    prestamos: list[Prestamo] = field(default_factory=list)
    productos: list[Producto] = field(default_factory=list)
    errores: list[str] = field(default_factory=list)


def _leer_inventario(ws) -> list[Producto]:
    """Lee la hoja «Inventario» generada por exportar_todo."""
    from services.inventario_importador import _detectar_columnas
    productos: list[Producto] = []

    # Detectar fila de encabezados en las primeras 5 filas
    header_row_idx = None
    mapa: dict = {}
    for row_idx in range(1, min(6, ws.max_row + 1)):
        fila = [ws.cell(row_idx, col).value for col in range(1, ws.max_column + 1)]
        celdas = sum(1 for x in fila if x is not None and str(x).strip())
        if celdas < 2:
            continue
        mapa = _detectar_columnas(fila)
        if mapa["producto"] is not None:
            header_row_idx = row_idx
            break

    if header_row_idx is None or mapa["producto"] is None:
        mapa = {"serial": 0, "producto": 1, "costo": 2, "cantidad": 3, "codigo_barras": 4}
        header_row_idx = 1

    for row_idx in range(header_row_idx + 1, ws.max_row + 1):
        col_prod = mapa.get("producto")
        val_prod = ws.cell(row_idx, (col_prod or 0) + 1).value if col_prod is not None else None
        if not val_prod or not str(val_prod).strip():
            continue

        def _get(campo, default):
            idx = mapa.get(campo)
            if idx is None:
                return default
            return ws.cell(row_idx, idx + 1).value

        serial = str(_get("serial", "") or "").strip()
        try:
            costo = float(_get("costo", 0) or 0)
        except (ValueError, TypeError):
            costo = 0.0
        try:
            cantidad = int(float(str(_get("cantidad", 0) or 0).replace(",", ".")))
        except (ValueError, TypeError):
            cantidad = 0
        cod = str(_get("codigo_barras", "") or "").strip()

        try:
            productos.append(Producto(
                serial=serial,
                producto=str(val_prod).strip(),
                costo_unitario=costo,
                cantidad=cantidad,
                codigo_barras=cod,
            ))
        except ValueError:
            pass
    return productos


def importar_todo(ruta: Path) -> ResultadoImportacionTotal:
    """
    Lee un .xlsx exportado por exportar_todo() y devuelve ventas, préstamos
    e inventario parseados.
    Espera hojas: «Ventas», «Préstamos», «Inventario».
    """
    resultado = ResultadoImportacionTotal()

    try:
        wb = openpyxl.load_workbook(str(ruta), data_only=True)
    except Exception as exc:
        resultado.errores.append(f"No se pudo abrir el archivo: {exc}")
        return resultado

    # ── Hoja Ventas ────────────────────────────────────────────────────────
    ws_v = next(
        (wb[s] for s in wb.sheetnames if s.lower() == "ventas"),
        None,
    )
    if ws_v is None:
        resultado.errores.append("No se encontró la hoja 'Ventas' en el archivo.")
    else:
        titulo = str(ws_v.cell(1, 1).value or "")
        parte = titulo.split("—")[-1].strip()  # "Abril 2026"
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

        for row_idx in range(4, ws_v.max_row + 1):
            col2 = ws_v.cell(row_idx, 2).value
            if col2 is None:
                continue
            if str(col2).upper().strip() == "TOTALES":
                break
            try:
                if isinstance(col2, datetime):
                    venta_fecha = col2.date()
                elif isinstance(col2, date):
                    venta_fecha = col2
                else:
                    venta_fecha = datetime.strptime(str(col2).strip(), "%d/%m/%Y").date()
            except (ValueError, TypeError):
                resultado.errores.append(f"Fila {row_idx}: fecha inválida — omitida")
                continue

            producto = str(ws_v.cell(row_idx, 3).value or "").strip()
            if not producto:
                continue
            try:
                cantidad = int(ws_v.cell(row_idx, 4).value or 1)
                if cantidad < 1:
                    cantidad = 1
            except (ValueError, TypeError):
                cantidad = 1
            try:
                costo = float(ws_v.cell(row_idx, 5).value or 0)
            except (ValueError, TypeError):
                costo = 0.0
            try:
                precio = float(ws_v.cell(row_idx, 6).value or 0)
            except (ValueError, TypeError):
                precio = 0.0
            metodo = str(ws_v.cell(row_idx, 7).value or "Efectivo").strip() or "Efectivo"
            try:
                comision = float(ws_v.cell(row_idx, 8).value or 0)
            except (ValueError, TypeError):
                comision = 0.0
            try:
                ganancia = float(ws_v.cell(row_idx, 9).value or 0)
            except (ValueError, TypeError):
                ganancia = 0.0
            notas = str(ws_v.cell(row_idx, 10).value or "").strip()
            try:
                resultado.ventas.append(Venta(
                    producto=producto, costo=costo, precio=precio,
                    metodo_pago=metodo, cantidad=cantidad,
                    comision=comision, ganancia_neta=ganancia,
                    notas=notas, fecha=venta_fecha,
                ))
            except ValueError as exc:
                resultado.errores.append(f"Fila {row_idx}: {exc} — omitida")

    # ── Hoja Préstamos ─────────────────────────────────────────────────────
    ws_p = next(
        (wb[s] for s in wb.sheetnames if s.lower() in ("préstamos", "prestamos")),
        None,
    )
    if ws_p:
        resultado.prestamos = _leer_prestamos(ws_p)

    # ── Hoja Inventario ────────────────────────────────────────────────────
    ws_i = next(
        (wb[s] for s in wb.sheetnames if s.lower() == "inventario"),
        None,
    )
    if ws_i:
        resultado.productos = _leer_inventario(ws_i)

    return resultado


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

        # ── Fecha — openpyxl puede devolver datetime (subclase de date) ──
        try:
            if isinstance(col2, datetime):
                venta_fecha = col2.date()
            elif isinstance(col2, date):
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

    # ── Leer hoja Préstamos si existe (acepta con o sin tilde) ────────
    hoja_prest = next(
        (s for s in wb.sheetnames if s.lower() in ("préstamos", "prestamos")),
        None,
    )
    if hoja_prest:
        resultado.prestamos = _leer_prestamos(wb[hoja_prest])

    return resultado
