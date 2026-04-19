"""
services/importador.py
Importa ventas desde un archivo .xlsx exportado por YJBMOTOCOM.
Sin dependencias de UI.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
import openpyxl

import json as _json

from models.venta import Venta
from models.prestamo import Prestamo
from models.producto import Producto
from models.factura import Factura
from models.gasto_dia import GastoDia, CATEGORIAS_GASTO
from models.configuracion import Configuracion
from utils.formatters import MESES_ES


# Lookup inverso: "enero" -> 1
_MES_NUM: dict[str, int] = {v.lower(): k for k, v in MESES_ES.items()}


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
    # Meses detectados desde las fechas de las ventas: {(año, mes), ...}
    meses_afectados: set = field(default_factory=set)
    prestamos: list[Prestamo] = field(default_factory=list)
    productos: list[Producto] = field(default_factory=list)
    facturas: list[Factura] = field(default_factory=list)
    gastos: list[GastoDia] = field(default_factory=list)
    meses_gastos_afectados: set = field(default_factory=set)
    configuracion: Configuracion | None = None
    errores: list[str] = field(default_factory=list)

    @property
    def año(self) -> int | None:
        if not self.meses_afectados:
            return None
        return sorted(self.meses_afectados)[0][0]

    @property
    def mes(self) -> int | None:
        if not self.meses_afectados:
            return None
        return sorted(self.meses_afectados)[0][1]


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


def _leer_facturas(ws) -> list[Factura]:
    """
    Lee la hoja «Facturas» generada por exportar_todo / generar_plantilla_todo.
    Fila 1 = título, fila 2 = encabezados, fila 3+ = datos.
    Columnas: Descripción | Proveedor | Monto | Fecha llegada | Fecha vencimiento | Estado | Notas
    (Versión anterior sin col 5 también soportada — detecta por encabezado)
    """
    # Detectar si la hoja tiene encabezado de "Fecha vencimiento" en col 5
    header_col5 = str(ws.cell(2, 5).value or "").strip().lower()
    tiene_vencimiento = "venc" in header_col5

    facturas: list[Factura] = []
    for row_idx in range(3, ws.max_row + 1):
        descripcion = str(ws.cell(row_idx, 1).value or "").strip()
        if not descripcion:
            continue

        proveedor = str(ws.cell(row_idx, 2).value or "").strip()

        try:
            monto = float(ws.cell(row_idx, 3).value or 0)
        except (ValueError, TypeError):
            monto = 0.0

        fecha_val = ws.cell(row_idx, 4).value
        try:
            if isinstance(fecha_val, datetime):
                fecha_obj = fecha_val.date()
            elif isinstance(fecha_val, date):
                fecha_obj = fecha_val
            else:
                fecha_obj = datetime.strptime(str(fecha_val).strip(), "%d/%m/%Y").date()
        except (ValueError, TypeError):
            fecha_obj = date.today()

        # Columnas desplazadas según versión del archivo
        fecha_pago = None
        if tiene_vencimiento:
            fv_val = ws.cell(row_idx, 5).value
            try:
                if isinstance(fv_val, datetime):
                    fecha_venc = fv_val.date()
                elif isinstance(fv_val, date):
                    fecha_venc = fv_val
                elif fv_val and str(fv_val).strip():
                    fecha_venc = datetime.strptime(str(fv_val).strip(), "%d/%m/%Y").date()
                else:
                    fecha_venc = None
            except (ValueError, TypeError):
                fecha_venc = None
            estado_raw = str(ws.cell(row_idx, 6).value or "pendiente").strip().lower()
            notas = str(ws.cell(row_idx, 7).value or "").strip()
            # Col 8 = fecha_pago (nuevo formato)
            fp_val = ws.cell(row_idx, 8).value
            try:
                if isinstance(fp_val, datetime):
                    fecha_pago = fp_val.date()
                elif isinstance(fp_val, date):
                    fecha_pago = fp_val
                elif fp_val and str(fp_val).strip():
                    fecha_pago = datetime.strptime(str(fp_val).strip(), "%d/%m/%Y").date()
            except (ValueError, TypeError):
                pass
        else:
            fecha_venc = None
            estado_raw = str(ws.cell(row_idx, 5).value or "pendiente").strip().lower()
            notas = str(ws.cell(row_idx, 6).value or "").strip()

        if estado_raw not in ("pendiente", "pagada"):
            estado_raw = "pendiente"

        try:
            facturas.append(Factura(
                descripcion=descripcion,
                proveedor=proveedor,
                monto=monto,
                fecha_llegada=fecha_obj,
                estado=estado_raw,
                notas=notas,
                fecha_vencimiento=fecha_venc,
                fecha_pago=fecha_pago,
            ))
        except ValueError:
            pass
    return facturas


def _leer_gastos(ws) -> list[GastoDia]:
    """
    Lee la hoja «Gastos» generada por exportar_todo.
    Fila 1 = título, fila 2 = encabezados, fila 3+ = datos.
    Columnas: Fecha | Descripción | Monto | Categoría (col 4, opcional)
    """
    gastos: list[GastoDia] = []
    for row_idx in range(3, ws.max_row + 1):
        fecha_val = ws.cell(row_idx, 1).value
        if fecha_val is None:
            continue
        try:
            if isinstance(fecha_val, datetime):
                fecha_obj = fecha_val.date()
            elif isinstance(fecha_val, date):
                fecha_obj = fecha_val
            else:
                fecha_obj = datetime.strptime(str(fecha_val).strip(), "%d/%m/%Y").date()
        except (ValueError, TypeError):
            continue

        descripcion = str(ws.cell(row_idx, 2).value or "").strip()
        if not descripcion:
            continue
        try:
            monto = float(ws.cell(row_idx, 3).value or 0)
        except (ValueError, TypeError):
            monto = 0.0

        cat_raw = str(ws.cell(row_idx, 4).value or "Otro").strip()
        categoria = cat_raw if cat_raw in CATEGORIAS_GASTO else "Otro"

        try:
            gastos.append(GastoDia(
                descripcion=descripcion,
                monto=monto,
                fecha=fecha_obj,
                categoria=categoria,
            ))
        except ValueError:
            pass
    return gastos


def _leer_configuracion(ws) -> Configuracion | None:
    """
    Lee la hoja «Configuración».
    Fila 1 = título, fila 2 = encabezados, fila 3 = valores.
    Columnas: Arriendo | Sueldo | Servicios | Otros gastos |
              Días mes | Comisión Bold | Comisión Addi | Comisión Transf.
    """
    if ws.max_row < 3:
        return None

    def _num(val, default=0.0):
        try:
            return float(val or default)
        except (ValueError, TypeError):
            return default

    def _int(val, default=30):
        try:
            return int(float(val or default))
        except (ValueError, TypeError):
            return default

    try:
        return Configuracion(
            arriendo=_num(ws.cell(3, 1).value),
            sueldo=_num(ws.cell(3, 2).value),
            servicios=_num(ws.cell(3, 3).value),
            otros_gastos=_num(ws.cell(3, 4).value),
            dias_mes=_int(ws.cell(3, 5).value),
            comision_bold=_num(ws.cell(3, 6).value),
            comision_addi=_num(ws.cell(3, 7).value),
            comision_transferencia=_num(ws.cell(3, 8).value),
        )
    except Exception:
        return None


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
            # Col 11: pagos_combinados JSON (solo existe en archivos exportados)
            pagos_raw = ws_v.cell(row_idx, 11).value
            pagos_combinados = None
            if pagos_raw:
                try:
                    pagos_combinados = _json.loads(str(pagos_raw))
                except Exception:
                    pass
            try:
                resultado.ventas.append(Venta(
                    producto=producto, costo=costo, precio=precio,
                    metodo_pago=metodo, cantidad=cantidad,
                    comision=comision, ganancia_neta=ganancia,
                    notas=notas, fecha=venta_fecha,
                    pagos_combinados=pagos_combinados,
                ))
                resultado.meses_afectados.add((venta_fecha.year, venta_fecha.month))
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

    # ── Hoja Facturas ──────────────────────────────────────────────────────
    ws_f = next(
        (wb[s] for s in wb.sheetnames if s.lower() == "facturas"),
        None,
    )
    if ws_f:
        resultado.facturas = _leer_facturas(ws_f)

    # ── Hoja Gastos ────────────────────────────────────────────────────────
    ws_g = next(
        (wb[s] for s in wb.sheetnames if s.lower() == "gastos"),
        None,
    )
    if ws_g:
        resultado.gastos = _leer_gastos(ws_g)
        for g in resultado.gastos:
            resultado.meses_gastos_afectados.add((g.fecha.year, g.fecha.month))

    # ── Hoja Configuración ─────────────────────────────────────────────────
    ws_c = next(
        (wb[s] for s in wb.sheetnames
         if s.lower() in ("configuración", "configuracion")),
        None,
    )
    if ws_c:
        resultado.configuracion = _leer_configuracion(ws_c)

    return resultado
