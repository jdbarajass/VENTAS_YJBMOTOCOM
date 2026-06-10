"""
services/pdf_reporte.py
Genera el reporte mensual en PDF usando reportlab.
Sin dependencias de UI.
"""

import re as _re
from pathlib import Path
from datetime import date
from collections import defaultdict

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
)

from services.reportes import ResumenMensual
from utils.formatters import cop, MESES_ES


# ── Paleta de colores ─────────────────────────────────────────────────────────
_AZUL_OSCURO  = colors.HexColor("#1E293B")
_AZUL_MEDIO   = colors.HexColor("#2563EB")
_AZUL_CLARO   = colors.HexColor("#DBEAFE")
_VERDE        = colors.HexColor("#16A34A")
_VERDE_CLARO  = colors.HexColor("#DCFCE7")
_ROJO         = colors.HexColor("#DC2626")
_ROJO_CLARO   = colors.HexColor("#FEE2E2")
_GRIS_CLARO   = colors.HexColor("#F1F5F9")
_GRIS_BORDE   = colors.HexColor("#E2E8F0")
_GRIS_TEXTO   = colors.HexColor("#6B7280")
_AMARILLO     = colors.HexColor("#D97706")
_MORADO       = colors.HexColor("#7C3AED")
_MORADO_CLARO = colors.HexColor("#EDE9FE")


# ── Utilidad de categorización ────────────────────────────────────────────────

def _categoria(nombre: str) -> str:
    """Extrae la categoría como la primera palabra del nombre (sin talla)."""
    limpio = _re.sub(r"\s*-T:\S*", "", nombre, flags=_re.IGNORECASE).strip()
    return limpio.split()[0].upper() if limpio else "OTRO"


# ── API pública ───────────────────────────────────────────────────────────────

def generar_reporte_mensual_pdf(
    resumen: ResumenMensual,
    ventas,
    ruta: Path,
    nombre_negocio: str = "YJBMOTOCOM",
    productos=None,          # list[Producto] — inventario actual (opcional)
) -> None:
    """
    Genera un PDF con el reporte mensual completo.
    ventas:    lista de Venta del mes.
    productos: lista de Producto del inventario actual (para sección inventario general).
    """
    doc = SimpleDocTemplate(
        str(ruta),
        pagesize=letter,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
        title=f"Reporte {MESES_ES.get(resumen.mes, '')} {resumen.año} — {nombre_negocio}",
    )

    estilos = getSampleStyleSheet()
    elementos = []

    # ── 1. Encabezado ─────────────────────────────────────────────────────────
    elementos += _encabezado(resumen, nombre_negocio, estilos)
    elementos.append(Spacer(1, 0.4 * cm))

    # ── 2. Tarjetas KPI ───────────────────────────────────────────────────────
    elementos.append(_tabla_resumen(resumen))
    elementos.append(Spacer(1, 0.5 * cm))

    # ── 3. Estadísticas adicionales ───────────────────────────────────────────
    elementos.append(_titulo_seccion("Estadísticas del Mes", estilos))
    elementos.append(_tabla_estadisticas(resumen, ventas))
    elementos.append(Spacer(1, 0.5 * cm))

    # ── 4. Top 10 Productos del mes ───────────────────────────────────────────
    elementos.append(_titulo_seccion("Top 10 Productos del Mes", estilos))
    elementos.append(_tabla_top_productos(ventas, resumen))
    elementos.append(Spacer(1, 0.5 * cm))

    # ── 5. Comisiones por método ──────────────────────────────────────────────
    elementos.append(_titulo_seccion("Comisiones por Método de Pago", estilos))
    elementos.append(_tabla_comisiones(ventas, resumen))
    elementos.append(Spacer(1, 0.5 * cm))

    # ── 6. Horas pico ─────────────────────────────────────────────────────────
    elementos.append(_titulo_seccion("Horas Pico de Ventas", estilos))
    elementos.append(_tabla_horas_pico(ventas))
    elementos.append(Spacer(1, 0.5 * cm))

    # ── 7. Resumen por día ────────────────────────────────────────────────────
    elementos.append(_titulo_seccion("Resumen por Día", estilos))
    elementos.append(_tabla_diaria(resumen))
    elementos.append(Spacer(1, 0.5 * cm))

    # ── 8. Inventario general (si se proveen productos) ───────────────────────
    if productos:
        elementos.append(_titulo_seccion("Inventario General (Stock Actual)", estilos))
        elementos.append(_tabla_inventario_general(productos))
        elementos.append(Spacer(1, 0.5 * cm))

    # ── 9. Pie de página ──────────────────────────────────────────────────────
    elementos.append(HRFlowable(width="100%", color=_GRIS_BORDE))
    elementos.append(Spacer(1, 0.2 * cm))
    pie = Paragraph(
        f"Generado el {date.today().strftime('%d/%m/%Y')}  •  {nombre_negocio} — Sistema de Control de Rentabilidad",
        ParagraphStyle("pie", fontSize=8, textColor=_GRIS_TEXTO, alignment=TA_CENTER),
    )
    elementos.append(pie)

    doc.build(elementos)


# ── Secciones ─────────────────────────────────────────────────────────────────

def _encabezado(resumen: ResumenMensual, nombre: str, estilos) -> list:
    mes_nombre = MESES_ES.get(resumen.mes, str(resumen.mes))
    titulo = Paragraph(
        f"<b>{nombre}</b>",
        ParagraphStyle("titulo", fontSize=22, textColor=_AZUL_OSCURO, alignment=TA_LEFT),
    )
    subtitulo = Paragraph(
        f"Reporte Mensual — {mes_nombre} {resumen.año}",
        ParagraphStyle("sub", fontSize=13, textColor=_AZUL_MEDIO, alignment=TA_LEFT),
    )
    return [titulo, Spacer(1, 0.3 * cm), subtitulo,
            Spacer(1, 0.35 * cm),
            HRFlowable(width="100%", color=_AZUL_MEDIO, thickness=2),
            Spacer(1, 0.5 * cm)]


def _titulo_seccion(texto: str, estilos) -> Paragraph:
    return Paragraph(
        f"<b>{texto}</b>",
        ParagraphStyle("seccion", fontSize=11, textColor=_AZUL_OSCURO,
                       spaceBefore=4, spaceAfter=4),
    )


def _tabla_resumen(resumen: ResumenMensual) -> Table:
    color_util = _VERDE if resumen.utilidad_real >= 0 else _ROJO
    fondo_util = _VERDE_CLARO if resumen.utilidad_real >= 0 else _ROJO_CLARO

    datos = [
        ["VENTAS DEL MES", "INGRESOS TOTALES", "GANANCIA NETA", "UTILIDAD REAL"],
        [
            str(resumen.cantidad_ventas),
            cop(resumen.total_ingresos),
            cop(resumen.ganancia_neta),
            cop(resumen.utilidad_real),
        ],
        [
            f"Días trabajados: {resumen.dias_con_ventas}",
            f"Costos: {cop(resumen.total_costos)}",
            f"Margen: {resumen.margen_ganancia:+.1f}%",
            f"Margen: {resumen.margen_utilidad:+.1f}%",
        ],
    ]

    col_w = [4.3 * cm] * 4
    t = Table(datos, colWidths=col_w)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), _AZUL_OSCURO),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 7.5),
        ("ALIGN",         (0, 0), (-1, 0), "CENTER"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 4),
        ("TOPPADDING",    (0, 0), (-1, 0), 5),
        ("FONTNAME",      (0, 1), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 1), (-1, 1), 14),
        ("ALIGN",         (0, 1), (-1, 1), "CENTER"),
        ("TEXTCOLOR",     (0, 1), (0,  1), _AZUL_MEDIO),
        ("TEXTCOLOR",     (1, 1), (1,  1), _AZUL_OSCURO),
        ("TEXTCOLOR",     (2, 1), (2,  1), _VERDE if resumen.ganancia_neta >= 0 else _ROJO),
        ("TEXTCOLOR",     (3, 1), (3,  1), color_util),
        ("BACKGROUND",    (3, 0), (3, -1), fondo_util),
        ("FONTSIZE",      (3, 1), (3,  1), 17),
        ("TOPPADDING",    (3, 1), (3,  1), 8),
        ("BOTTOMPADDING", (3, 1), (3,  1), 8),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 4),
        ("TOPPADDING",    (0, 1), (-1, 1), 6),
        ("FONTSIZE",      (0, 2), (-1, 2), 8),
        ("TEXTCOLOR",     (0, 2), (-1, 2), _GRIS_TEXTO),
        ("ALIGN",         (0, 2), (-1, 2), "CENTER"),
        ("BOTTOMPADDING", (0, 2), (-1, 2), 6),
        ("GRID",          (0, 0), (-1, -1), 0.5, _GRIS_BORDE),
        ("ROUNDEDCORNERS", [4]),
    ]))
    return t


def _tabla_estadisticas(resumen: ResumenMensual, ventas) -> Table:
    """Tarjetas 2×2 con estadísticas adicionales del mes."""
    # Método más usado
    conteo_metodo: dict[str, int] = defaultdict(int)
    total_ingresos_mes = resumen.total_ingresos or 1
    cat_ventas: dict[str, int] = defaultdict(int)
    for v in ventas:
        conteo_metodo[v.metodo_pago] += v.cantidad
        cat_ventas[_categoria(v.producto)] += v.cantidad

    metodo_top = max(conteo_metodo, key=lambda k: conteo_metodo[k]) if conteo_metodo else "—"
    cat_top = max(cat_ventas, key=lambda k: cat_ventas[k]) if cat_ventas else "—"

    # Ticket promedio
    ticket = resumen.total_ingresos / resumen.cantidad_ventas if resumen.cantidad_ventas else 0

    # Día más rentable
    dia_top = max(resumen.resumen_por_dia, key=lambda d: d.ganancia_neta,
                  default=None)
    dia_top_str = dia_top.fecha.strftime("%d/%m") if dia_top else "—"

    datos = [
        ["MÉTODO MÁS USADO", "TICKET PROMEDIO", "CATEGORÍA TOP", "DÍA MÁS RENTABLE"],
        [metodo_top, cop(ticket), cat_top, dia_top_str],
        [
            f"{conteo_metodo.get(metodo_top, 0)} uds.",
            "Por transacción",
            f"{cat_ventas.get(cat_top, 0)} uds.",
            f"G.Neta: {cop(dia_top.ganancia_neta)}" if dia_top else "—",
        ],
    ]

    col_w = [4.3 * cm] * 4
    t = Table(datos, colWidths=col_w)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), _MORADO),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 7.5),
        ("ALIGN",         (0, 0), (-1, 0), "CENTER"),
        ("TOPPADDING",    (0, 0), (-1, 0), 5),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 4),
        ("BACKGROUND",    (0, 1), (-1, 2), _MORADO_CLARO),
        ("FONTNAME",      (0, 1), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 1), (-1, 1), 12),
        ("ALIGN",         (0, 1), (-1, 1), "CENTER"),
        ("TEXTCOLOR",     (0, 1), (-1, 1), _MORADO),
        ("FONTSIZE",      (0, 2), (-1, 2), 8),
        ("TEXTCOLOR",     (0, 2), (-1, 2), _GRIS_TEXTO),
        ("ALIGN",         (0, 2), (-1, 2), "CENTER"),
        ("BOTTOMPADDING", (0, 2), (-1, 2), 6),
        ("GRID",          (0, 0), (-1, -1), 0.5, _GRIS_BORDE),
    ]))
    return t


def _tabla_top_productos(ventas, resumen: ResumenMensual) -> Table:
    """Top 10 productos del mes por unidades vendidas."""
    por_producto: dict[str, dict] = defaultdict(lambda: {"cantidad": 0, "ingresos": 0.0})
    for v in ventas:
        nombre = _re.sub(r"\s*-T:\S*", "", v.producto, flags=_re.IGNORECASE).strip()
        por_producto[nombre]["cantidad"] += v.cantidad
        por_producto[nombre]["ingresos"] += v.precio * v.cantidad

    top = sorted(por_producto.items(), key=lambda x: -x[1]["cantidad"])[:10]

    if not top:
        datos = [["Sin ventas registradas en este período"]]
        t = Table(datos, colWidths=[17.3 * cm])
        t.setStyle(TableStyle([
            ("ALIGN",        (0, 0), (-1, -1), "CENTER"),
            ("TEXTCOLOR",    (0, 0), (-1, -1), _GRIS_TEXTO),
            ("FONTSIZE",     (0, 0), (-1, -1), 9),
            ("TOPPADDING",   (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 8),
        ]))
        return t

    total_ingresos = resumen.total_ingresos or 1
    encabezado = [["#", "PRODUCTO", "CANT.", "INGRESOS", "% PART."]]
    filas = []
    for i, (nombre, stats) in enumerate(top, 1):
        pct = stats["ingresos"] / total_ingresos * 100
        filas.append([
            str(i),
            nombre,
            str(stats["cantidad"]),
            cop(stats["ingresos"]),
            f"{pct:.2f}%",
        ])

    datos = encabezado + filas
    col_w = [0.8*cm, 9.5*cm, 1.8*cm, 3.2*cm, 2.0*cm]
    t = Table(datos, colWidths=col_w, repeatRows=1)
    n = len(datos)
    estilos_t = [
        ("BACKGROUND",    (0, 0), (-1, 0), _AZUL_OSCURO),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 8),
        ("ALIGN",         (0, 0), (-1, 0), "CENTER"),
        ("FONTSIZE",      (0, 1), (-1, -1), 8.5),
        ("ALIGN",         (0, 1), (0, -1), "CENTER"),
        ("ALIGN",         (2, 1), (2, -1), "CENTER"),
        ("ALIGN",         (3, 1), (4, -1), "RIGHT"),
        ("TEXTCOLOR",     (3, 1), (3, -1), _VERDE),
        ("TEXTCOLOR",     (4, 1), (4, -1), _AZUL_MEDIO),
        ("FONTNAME",      (0, 1), (0, 3),  "Helvetica-Bold"),
        ("GRID",          (0, 0), (-1, -1), 0.4, _GRIS_BORDE),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, _GRIS_CLARO]),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    # Top 3 en negrita
    for i in range(1, min(4, n)):
        estilos_t.append(("FONTNAME", (1, i), (1, i), "Helvetica-Bold"))
    t.setStyle(TableStyle(estilos_t))
    return t


def _tabla_comisiones(ventas, resumen: ResumenMensual) -> Table:
    totales: dict[str, float] = defaultdict(float)
    conteo: dict[str, int] = defaultdict(int)
    for v in ventas:
        if v.comision > 0:
            totales[v.metodo_pago] += v.comision
            conteo[v.metodo_pago] += 1

    if not totales:
        datos = [["Sin comisiones registradas en este período"]]
        t = Table(datos, colWidths=[17.3 * cm])
        t.setStyle(TableStyle([
            ("ALIGN",        (0, 0), (-1, -1), "CENTER"),
            ("TEXTCOLOR",    (0, 0), (-1, -1), _GRIS_TEXTO),
            ("FONTSIZE",     (0, 0), (-1, -1), 9),
            ("TOPPADDING",   (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 8),
        ]))
        return t

    encabezado = [["MÉTODO", "VENTAS CON COMISIÓN", "TOTAL COMISIÓN"]]
    filas = [
        [metodo, str(conteo[metodo]), cop(monto)]
        for metodo, monto in sorted(totales.items(), key=lambda x: -x[1])
    ]
    filas.append(["TOTAL", str(sum(conteo.values())), cop(resumen.total_comisiones)])

    datos = encabezado + filas
    col_w = [6 * cm, 5.5 * cm, 5.8 * cm]
    t = Table(datos, colWidths=col_w)
    n = len(datos)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), _AZUL_OSCURO),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 8),
        ("ALIGN",         (0, 0), (-1, 0), "CENTER"),
        ("FONTSIZE",      (0, 1), (-1, -2), 9),
        ("ALIGN",         (1, 1), (-1, -1), "CENTER"),
        ("BACKGROUND",    (0, n-1), (-1, n-1), _GRIS_CLARO),
        ("FONTNAME",      (0, n-1), (-1, n-1), "Helvetica-Bold"),
        ("TEXTCOLOR",     (2, 1), (2, n-2), _ROJO),
        ("TEXTCOLOR",     (2, n-1), (2, n-1), _ROJO),
        ("GRID",          (0, 0), (-1, -1), 0.5, _GRIS_BORDE),
        ("ROWBACKGROUNDS",(0, 1), (-1, n-2), [colors.white, _GRIS_CLARO]),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


def _tabla_horas_pico(ventas) -> Table:
    """Distribución de ventas por franja horaria."""
    por_hora: dict[int, int] = defaultdict(int)
    ingresos_hora: dict[int, float] = defaultdict(float)

    ventas_con_hora = [v for v in ventas if getattr(v, "hora", "") and len(v.hora) >= 4]

    if not ventas_con_hora:
        nota = Paragraph(
            "Aún no hay datos de hora registrados. A partir de ahora cada venta "
            "guardará su hora automáticamente y aparecerá en este reporte.",
            ParagraphStyle("nota_hora", fontSize=8.5, textColor=_GRIS_TEXTO,
                           alignment=TA_LEFT, leftIndent=4),
        )
        datos = [["Sin datos de hora disponibles"]]
        t = Table(datos, colWidths=[17.3 * cm])
        t.setStyle(TableStyle([
            ("ALIGN",        (0, 0), (-1, -1), "CENTER"),
            ("TEXTCOLOR",    (0, 0), (-1, -1), _GRIS_TEXTO),
            ("FONTSIZE",     (0, 0), (-1, -1), 9),
            ("FONTNAME",     (0, 0), (-1, -1), "Helvetica-Oblique"),
            ("TOPPADDING",   (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 8),
            ("BACKGROUND",   (0, 0), (-1, -1), _GRIS_CLARO),
            ("GRID",         (0, 0), (-1, -1), 0.4, _GRIS_BORDE),
        ]))
        return t

    for v in ventas_con_hora:
        try:
            h = int(v.hora[:2])
            por_hora[h] += v.cantidad
            ingresos_hora[h] += v.precio * v.cantidad
        except ValueError:
            pass

    # Franjas de 2 horas de 6am a 22pm
    franjas = [
        (6, 8), (8, 10), (10, 12), (12, 14),
        (14, 16), (16, 18), (18, 20), (20, 22),
    ]
    total_uds = sum(por_hora.values()) or 1

    encabezado = [["FRANJA HORARIA", "UNIDADES VENDIDAS", "INGRESOS", "% DEL MES"]]
    filas = []
    for h_ini, h_fin in franjas:
        uds = sum(por_hora[h] for h in range(h_ini, h_fin))
        ing = sum(ingresos_hora[h] for h in range(h_ini, h_fin))
        pct = uds / total_uds * 100
        filas.append([
            f"{h_ini:02d}:00 – {h_fin:02d}:00",
            str(uds) if uds else "—",
            cop(ing) if ing else "—",
            f"{pct:.1f}%" if uds else "—",
        ])

    datos = encabezado + filas
    col_w = [4.5*cm, 4.0*cm, 5.3*cm, 3.5*cm]
    t = Table(datos, colWidths=col_w)
    n = len(datos)

    # Encontrar franja pico para destacarla
    max_uds = max((sum(por_hora[h] for h in range(hi, hf)) for hi, hf in franjas), default=0)

    estilos_t = [
        ("BACKGROUND",    (0, 0), (-1, 0), _AZUL_OSCURO),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 8),
        ("ALIGN",         (0, 0), (-1, 0), "CENTER"),
        ("FONTSIZE",      (0, 1), (-1, -1), 8.5),
        ("ALIGN",         (0, 1), (-1, -1), "CENTER"),
        ("TEXTCOLOR",     (2, 1), (2, -1), _VERDE),
        ("TEXTCOLOR",     (3, 1), (3, -1), _AZUL_MEDIO),
        ("GRID",          (0, 0), (-1, -1), 0.4, _GRIS_BORDE),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, _GRIS_CLARO]),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    # Destacar franja pico
    for i, (h_ini, h_fin) in enumerate(franjas, 1):
        uds_f = sum(por_hora[h] for h in range(h_ini, h_fin))
        if uds_f == max_uds and max_uds > 0:
            estilos_t.append(("BACKGROUND", (0, i), (-1, i), _AZUL_CLARO))
            estilos_t.append(("FONTNAME",   (0, i), (-1, i), "Helvetica-Bold"))
            estilos_t.append(("TEXTCOLOR",  (0, i), (0, i), _AZUL_MEDIO))

    t.setStyle(TableStyle(estilos_t))
    return t


def _tabla_diaria(resumen: ResumenMensual) -> Table:
    encabezado = [["FECHA", "VENTAS", "INGRESOS", "G. NETA", "GASTOS OP.", "UTILIDAD", "ESTADO"]]

    filas = []
    for rd in resumen.resumen_por_dia:
        filas.append([
            rd.fecha.strftime("%d/%m/%Y"),
            str(rd.cantidad_ventas),
            cop(rd.total_ingresos),
            cop(rd.ganancia_neta),
            cop(rd.gastos_operativos) if rd.gastos_operativos > 0 else "—",
            cop(rd.utilidad_real),
            "Positivo" if rd.es_positivo else "Negativo",
        ])

    if not filas:
        filas = [["Sin ventas registradas", "", "", "", "", "", ""]]

    datos = encabezado + filas
    col_w = [2.4*cm, 1.5*cm, 2.8*cm, 2.7*cm, 2.6*cm, 2.7*cm, 2.1*cm]
    t = Table(datos, colWidths=col_w, repeatRows=1)

    estilos_tabla = [
        ("BACKGROUND",    (0, 0), (-1, 0), _AZUL_OSCURO),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 7.5),
        ("ALIGN",         (0, 0), (-1, 0), "CENTER"),
        ("FONTSIZE",      (0, 1), (-1, -1), 8),
        ("ALIGN",         (0, 1), (1, -1), "CENTER"),
        ("ALIGN",         (2, 1), (5, -1), "RIGHT"),
        ("ALIGN",         (6, 1), (6, -1), "CENTER"),
        ("GRID",          (0, 0), (-1, -1), 0.4, _GRIS_BORDE),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, _GRIS_CLARO]),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]

    for i, rd in enumerate(resumen.resumen_por_dia, start=1):
        color_util = _VERDE if rd.utilidad_real >= 0 else _ROJO
        color_est  = _VERDE if rd.es_positivo     else _ROJO
        estilos_tabla.append(("TEXTCOLOR", (5, i), (5, i), color_util))
        estilos_tabla.append(("TEXTCOLOR", (6, i), (6, i), color_est))

    t.setStyle(TableStyle(estilos_tabla))
    return t


def _tabla_inventario_general(productos) -> Table:
    """Inventario agrupado por categoría (primera palabra del nombre)."""
    grupos: dict[str, dict] = defaultdict(lambda: {"referencias": 0, "unidades": 0, "valor": 0.0})
    for p in productos:
        cat = _categoria(p.producto)
        grupos[cat]["referencias"] += 1
        grupos[cat]["unidades"] += p.cantidad
        grupos[cat]["valor"] += p.costo_unitario * p.cantidad

    # Ordenar por unidades descendente
    ordenados = sorted(grupos.items(), key=lambda x: -x[1]["unidades"])

    total_ref = sum(g["referencias"] for g in grupos.values())
    total_uds = sum(g["unidades"] for g in grupos.values())
    total_val = sum(g["valor"] for g in grupos.values())

    encabezado = [["CATEGORÍA", "REFERENCIAS", "UNIDADES EN STOCK", "VALOR EN STOCK"]]
    filas = [
        [cat, str(d["referencias"]), str(d["unidades"]), cop(d["valor"])]
        for cat, d in ordenados
    ]
    filas.append(["TOTAL", str(total_ref), str(total_uds), cop(total_val)])

    datos = encabezado + filas
    col_w = [6.0*cm, 3.5*cm, 4.3*cm, 3.5*cm]
    t = Table(datos, colWidths=col_w, repeatRows=1)
    n = len(datos)

    estilos_t = [
        ("BACKGROUND",    (0, 0), (-1, 0), _AZUL_OSCURO),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 8),
        ("ALIGN",         (0, 0), (-1, 0), "CENTER"),
        ("FONTSIZE",      (0, 1), (-1, -1), 8.5),
        ("ALIGN",         (0, 1), (0, -1), "LEFT"),
        ("ALIGN",         (1, 1), (-1, -1), "CENTER"),
        ("TEXTCOLOR",     (2, 1), (2, n-2), _VERDE),
        ("TEXTCOLOR",     (3, 1), (3, n-2), _AZUL_MEDIO),
        # Fila de totales
        ("BACKGROUND",    (0, n-1), (-1, n-1), _GRIS_CLARO),
        ("FONTNAME",      (0, n-1), (-1, n-1), "Helvetica-Bold"),
        ("TEXTCOLOR",     (2, n-1), (2, n-1), _AZUL_OSCURO),
        ("TEXTCOLOR",     (3, n-1), (3, n-1), _AZUL_OSCURO),
        ("GRID",          (0, 0), (-1, -1), 0.4, _GRIS_BORDE),
        ("ROWBACKGROUNDS",(0, 1), (-1, n-2), [colors.white, _GRIS_CLARO]),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 1), (0, -1), 8),
    ]
    t.setStyle(TableStyle(estilos_t))
    return t
