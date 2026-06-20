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
from reportlab.graphics.shapes import Drawing, String, Rect, Line, Group
from reportlab.graphics import renderPDF
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie

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

def _categoria(p) -> str:
    """Categoría explícita si existe; si no, inferida de la primera palabra del nombre."""
    if hasattr(p, "categoria") and p.categoria:
        return p.categoria.strip().upper()
    nombre = p.producto if hasattr(p, "producto") else str(p)
    limpio = _re.sub(r"\s*-T:\S*", "", nombre, flags=_re.IGNORECASE).strip()
    return limpio.split()[0].upper() if limpio else "OTRO"


# ── API pública ───────────────────────────────────────────────────────────────

def generar_reporte_mensual_pdf(
    resumen: ResumenMensual,
    ventas,
    ruta: Path,
    nombre_negocio: str = "YJBMOTOCOM",
    productos=None,   # list[Producto] — inventario actual (opcional)
    cfg=None,         # Configuracion — para desglose de gastos fijos
) -> None:
    """
    Genera un PDF con el reporte mensual completo.
    ventas:    lista de Venta del mes.
    productos: lista de Producto del inventario actual (para sección inventario general).
    cfg:       Configuracion para mostrar el desglose de gastos fijos.
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
    elementos.append(Spacer(1, 0.4 * cm))

    # ── 2.5. Desglose de gastos ───────────────────────────────────────────────
    elementos.append(_titulo_seccion("Desglose de Gastos del Mes", estilos))
    elementos.append(_tabla_gastos(resumen, cfg))
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

    # ── 7.5. Gráficas ─────────────────────────────────────────────────────────
    grafica_dias = _grafica_ingresos_diarios(resumen)
    if grafica_dias is not None:
        elementos.append(_titulo_seccion("Ingresos Diarios", estilos))
        elementos.append(grafica_dias)
        elementos.append(Spacer(1, 0.5 * cm))

    grafica_metodos = _grafica_metodos_pago(ventas)
    if grafica_metodos is not None:
        elementos.append(_titulo_seccion("Ingresos por Método de Pago", estilos))
        elementos.append(grafica_metodos)
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
    color_util_hex = "#16A34A" if resumen.utilidad_real >= 0 else "#DC2626"

    # Celda UTILIDAD REAL como Paragraph fusionado (sin líneas internas)
    util_cell = Paragraph(
        f'<font name="Helvetica-Bold" size="8" color="{color_util_hex}">UTILIDAD REAL</font>'
        f'<br/><br/>'
        f'<font name="Helvetica-Bold" size="16" color="{color_util_hex}">{cop(resumen.utilidad_real)}</font>'
        f'<br/><br/>'
        f'<font name="Helvetica" size="8" color="#6B7280">Margen: {resumen.margen_utilidad:+.1f}%</font>',
        ParagraphStyle("util_cell", alignment=TA_CENTER, leading=22),
    )

    datos = [
        ["VENTAS DEL MES", "INGRESOS TOTALES", "GANANCIA NETA", util_cell],
        [str(resumen.cantidad_ventas), cop(resumen.total_ingresos), cop(resumen.ganancia_neta), ""],
        [f"Días trabajados: {resumen.dias_con_ventas}", f"Costos: {cop(resumen.total_costos)}", f"Margen: {resumen.margen_ganancia:+.1f}%", ""],
    ]

    col_w = [4.3 * cm] * 4
    t = Table(datos, colWidths=col_w)
    t.setStyle(TableStyle([
        # Columnas 0-2: encabezado oscuro
        ("BACKGROUND",    (0, 0), (2, 0), _AZUL_OSCURO),
        ("TEXTCOLOR",     (0, 0), (2, 0), colors.white),
        ("FONTNAME",      (0, 0), (2, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (2, 0), 7.5),
        ("ALIGN",         (0, 0), (2, 0), "CENTER"),
        ("BOTTOMPADDING", (0, 0), (2, 0), 4),
        ("TOPPADDING",    (0, 0), (2, 0), 5),
        # Columnas 0-2: fila de valores
        ("FONTNAME",      (0, 1), (2, 1), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 1), (2, 1), 14),
        ("ALIGN",         (0, 1), (2, 1), "CENTER"),
        ("TEXTCOLOR",     (0, 1), (0, 1), _AZUL_MEDIO),
        ("TEXTCOLOR",     (1, 1), (1, 1), _AZUL_OSCURO),
        ("TEXTCOLOR",     (2, 1), (2, 1), _VERDE if resumen.ganancia_neta >= 0 else _ROJO),
        ("BOTTOMPADDING", (0, 1), (2, 1), 4),
        ("TOPPADDING",    (0, 1), (2, 1), 6),
        # Columnas 0-2: subtítulo
        ("FONTSIZE",      (0, 2), (2, 2), 8),
        ("TEXTCOLOR",     (0, 2), (2, 2), _GRIS_TEXTO),
        ("ALIGN",         (0, 2), (2, 2), "CENTER"),
        ("BOTTOMPADDING", (0, 2), (2, 2), 6),
        # UTILIDAD REAL: celda fusionada — sin líneas internas posibles
        ("SPAN",          (3, 0), (3, 2)),
        ("BACKGROUND",    (3, 0), (3, 2), fondo_util),
        ("VALIGN",        (3, 0), (3, 2), "MIDDLE"),
        ("ALIGN",         (3, 0), (3, 2), "CENTER"),
        # Borde general
        ("GRID",          (0, 0), (-1, -1), 0.5, _GRIS_BORDE),
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
        por_producto[nombre]["ingresos"] += v.ingreso_real()

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
    _estilo_top_n  = ParagraphStyle(
        "top_nom", fontName="Helvetica", fontSize=8.5,
        leading=11, wordWrap="CJK",
    )
    _estilo_top_b  = ParagraphStyle(
        "top_nom_b", fontName="Helvetica-Bold", fontSize=8.5,
        leading=11, wordWrap="CJK",
    )
    encabezado = [["#", "PRODUCTO", "CANT.", "INGRESOS", "% PART."]]
    filas = []
    for i, (nombre, stats) in enumerate(top, 1):
        pct = stats["ingresos"] / total_ingresos * 100
        estilo_p = _estilo_top_b if i <= 3 else _estilo_top_n
        filas.append([
            str(i),
            Paragraph(nombre, estilo_p),
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
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]
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
            ingresos_hora[h] += v.ingreso_real()
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


def _tabla_gastos(resumen: ResumenMensual, cfg=None) -> Table:
    """Desglose de gastos fijos + operativos del mes."""
    total_op = round(sum(rd.gastos_operativos for rd in resumen.resumen_por_dia), 2)
    total_fijos = resumen.total_gastos_fijos
    total_egresos = round(total_fijos + total_op, 2)

    encabezado = [["CONCEPTO", "MONTO"]]
    filas: list = []

    if cfg is not None:
        for label, monto in [
            ("Arriendo",           cfg.arriendo),
            ("Sueldo",             cfg.sueldo),
            ("Servicios públicos", cfg.servicios),
            ("Otros gastos fijos", cfg.otros_gastos),
        ]:
            filas.append([label, cop(monto)])

    idx_total_fijos = len(filas) + 1   # índice en la tabla (con encabezado)
    filas.append(["Total gastos fijos", cop(total_fijos)])

    idx_op = len(filas) + 1
    filas.append(["Gastos operativos del mes", cop(total_op)])

    idx_total = len(filas) + 1
    filas.append(["TOTAL EGRESOS DEL MES", cop(total_egresos)])

    datos = encabezado + filas
    col_w = [12.0 * cm, 5.3 * cm]
    t = Table(datos, colWidths=col_w)

    estilos_t = [
        ("BACKGROUND",    (0, 0), (-1, 0), _AZUL_OSCURO),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 8),
        ("ALIGN",         (0, 0), (-1, 0), "CENTER"),
        ("FONTSIZE",      (0, 1), (-1, -1), 9),
        ("ALIGN",         (1, 1), (1, -1), "RIGHT"),
        ("LEFTPADDING",   (0, 1), (0, -1), 12),
        ("GRID",          (0, 0), (-1, -1), 0.4, _GRIS_BORDE),
        ("ROWBACKGROUNDS",(0, 1), (-1, idx_total - 2), [colors.white, _GRIS_CLARO]),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        # Fila total gastos fijos
        ("BACKGROUND",    (0, idx_total_fijos), (-1, idx_total_fijos), _GRIS_CLARO),
        ("FONTNAME",      (0, idx_total_fijos), (-1, idx_total_fijos), "Helvetica-Bold"),
        ("TEXTCOLOR",     (1, idx_total_fijos), (1, idx_total_fijos), _ROJO),
        # Fila gastos operativos
        ("FONTNAME",      (0, idx_op), (0, idx_op), "Helvetica-Oblique"),
        ("TEXTCOLOR",     (1, idx_op), (1, idx_op), _AMARILLO),
        # Fila total egresos
        ("BACKGROUND",    (0, idx_total), (-1, idx_total), _ROJO_CLARO),
        ("FONTNAME",      (0, idx_total), (-1, idx_total), "Helvetica-Bold"),
        ("FONTSIZE",      (0, idx_total), (-1, idx_total), 10),
        ("TEXTCOLOR",     (1, idx_total), (1, idx_total), _ROJO),
        ("TOPPADDING",    (0, idx_total), (-1, idx_total), 7),
        ("BOTTOMPADDING", (0, idx_total), (-1, idx_total), 7),
    ]
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
        cat = _categoria(p)
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


# ─────────────────────────────────────────────────────────────────────────────
# Gráficas
# ─────────────────────────────────────────────────────────────────────────────

def _grafica_ingresos_diarios(resumen: ResumenMensual) -> Drawing | None:
    """
    Gráfica de barras verticales con ingresos por día.
    Retorna None si no hay datos.
    """
    dias = resumen.resumen_por_dia
    if not dias:
        return None

    W, H = 480, 200
    drawing = Drawing(W, H)

    valores = [rd.total_ingresos for rd in dias]
    etiquetas = [str(rd.fecha.day) for rd in dias]
    maximo = max(valores) if any(v > 0 for v in valores) else 1

    bar_w = (W - 60) / max(len(valores), 1)
    barra_ancho = bar_w * 0.65
    inicio_x = 50

    # Eje Y — líneas de guía y etiquetas
    for factor in (0, 0.25, 0.5, 0.75, 1.0):
        y = 30 + factor * (H - 50)
        drawing.add(Line(45, y, W - 10, y,
                         strokeColor=colors.HexColor("#E5E7EB"), strokeWidth=0.5))
        monto = maximo * factor
        lbl = String(40, y - 4, cop(monto) if monto > 0 else "0",
                     fontSize=6, fillColor=colors.HexColor("#9CA3AF"),
                     textAnchor="end")
        drawing.add(lbl)

    # Barras
    for i, (val, dia_lbl) in enumerate(zip(valores, etiquetas)):
        x = inicio_x + i * bar_w + (bar_w - barra_ancho) / 2
        h_barra = (val / maximo) * (H - 50) if maximo > 0 else 0
        color_barra = colors.HexColor("#2563EB") if val > 0 else colors.HexColor("#E5E7EB")
        drawing.add(Rect(x, 30, barra_ancho, h_barra,
                         fillColor=color_barra, strokeColor=None))
        # Etiqueta día
        drawing.add(String(x + barra_ancho / 2, 18, dia_lbl,
                           fontSize=6, fillColor=colors.HexColor("#6B7280"),
                           textAnchor="middle"))

    return drawing


def _grafica_metodos_pago(ventas) -> Drawing | None:
    """
    Gráfica de barras horizontales con ingresos por método de pago.
    Retorna None si no hay ventas.
    """
    from collections import defaultdict
    por_metodo: dict[str, float] = defaultdict(float)
    for v in ventas:
        metodo = (v.metodo_pago or "Otro").strip()
        por_metodo[metodo] += v.ingreso_real()

    if not por_metodo:
        return None

    ordenados = sorted(por_metodo.items(), key=lambda x: -x[1])[:8]
    maximo = ordenados[0][1] if ordenados else 1

    W, H = 480, max(80, len(ordenados) * 30 + 20)
    drawing = Drawing(W, H)

    COLORES_BARRAS = [
        "#2563EB", "#15803D", "#D97706", "#7C3AED",
        "#0891B2", "#DC2626", "#065F46", "#92400E",
    ]
    barra_h = 18
    inicio_y = H - 20
    inicio_x = 140

    for i, (metodo, monto) in enumerate(ordenados):
        y = inicio_y - i * 30
        ancho_barra = (monto / maximo) * (W - inicio_x - 80) if maximo > 0 else 0
        color_b = colors.HexColor(COLORES_BARRAS[i % len(COLORES_BARRAS)])

        # Etiqueta método
        drawing.add(String(inicio_x - 4, y - 5, metodo[:22],
                           fontSize=7.5, fillColor=colors.HexColor("#374151"),
                           textAnchor="end"))

        # Barra
        drawing.add(Rect(inicio_x, y - barra_h + 4, ancho_barra, barra_h,
                         fillColor=color_b, strokeColor=None))

        # Valor al final
        drawing.add(String(inicio_x + ancho_barra + 4, y - 5, cop(monto),
                           fontSize=7, fillColor=color_b, textAnchor="start"))

    return drawing


# ─────────────────────────────────────────────────────────────────────────────
# PDF Listado de Inventario
# ─────────────────────────────────────────────────────────────────────────────

def generar_pdf_inventario(
    productos,          # list[Producto]
    ruta: Path,
    nombre_negocio: str = "YJBMOTOCOM",
    alcance: str = "todos",            # "todos" | "con_stock" | "bajo_minimo"
    categoria: str | None = None,      # filtra por categoría exacta (None = todas)
    talla: str | None = None,          # filtra por talla; "" = sin talla, None = todas
    orden: str = "nombre",             # "nombre" | "categoria" | "stock_desc" | "stock_asc"
    incluir_resumen_categorias: bool = True,
) -> None:
    """Genera un PDF con el listado de inventario, aplicando los filtros y el
    orden indicados. Opcionalmente agrega una tabla resumen agrupada por categoría."""
    from datetime import datetime

    doc = SimpleDocTemplate(
        str(ruta),
        pagesize=letter,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
        title=f"Inventario — {nombre_negocio}",
    )

    estilos = getSampleStyleSheet()
    elementos = []

    # ── Encabezado ────────────────────────────────────────────────────────────
    elementos.append(Paragraph(
        f'<font color="#1E293B"><b>{nombre_negocio}</b></font>',
        ParagraphStyle("titulo", fontName="Helvetica-Bold", fontSize=18,
                       alignment=TA_LEFT, spaceAfter=2),
    ))
    elementos.append(Paragraph(
        "Listado de Inventario",
        ParagraphStyle("subtitulo", fontName="Helvetica", fontSize=13,
                       textColor=colors.HexColor("#2563EB"), spaceAfter=4),
    ))
    ahora = datetime.now().strftime("%d/%m/%Y  %H:%M")

    # ── Aplicar filtros ────────────────────────────────────────────────────────
    prods_filtrados = list(productos)
    if alcance == "con_stock":
        prods_filtrados = [p for p in prods_filtrados if p.cantidad > 0]
    elif alcance == "bajo_minimo":
        prods_filtrados = [
            p for p in prods_filtrados
            if p.stock_minimo > 0 and p.cantidad < p.stock_minimo
        ]

    if categoria:
        cat_sel = categoria.strip().upper()
        prods_filtrados = [p for p in prods_filtrados if _categoria(p) == cat_sel]

    if talla is not None:
        if talla == "":
            prods_filtrados = [p for p in prods_filtrados if not p.talla]
        else:
            prods_filtrados = [p for p in prods_filtrados if p.talla == talla]

    _ALCANCE_TXT = {
        "todos": "Todos los productos",
        "con_stock": "Solo con stock",
        "bajo_minimo": "Solo bajo el mínimo",
    }
    partes_filtro = [_ALCANCE_TXT.get(alcance, "Todos los productos")]
    if categoria:
        partes_filtro.append(f"Categoría: {categoria}")
    if talla is not None:
        partes_filtro.append(f"Talla: {talla or 'Sin talla'}")
    filtro_txt = "  •  ".join(partes_filtro)

    elementos.append(Paragraph(
        f'Generado: {ahora}  •  {filtro_txt}',
        ParagraphStyle("meta", fontName="Helvetica", fontSize=8,
                       textColor=colors.HexColor("#6B7280"), spaceAfter=6),
    ))
    elementos.append(HRFlowable(width="100%", thickness=1, color=_AZUL_OSCURO,
                                spaceAfter=10))

    # ── Resumen superior ──────────────────────────────────────────────────────
    total_refs  = len(prods_filtrados)
    total_uds   = sum(p.cantidad for p in prods_filtrados)
    total_costo = sum(p.costo_unitario * p.cantidad for p in prods_filtrados)

    resumen_data = [
        ["REFERENCIAS", "UNIDADES EN STOCK", "VALOR EN COSTO"],
        [str(total_refs), str(total_uds), cop(total_costo)],
    ]
    col_w_res = [4.5*cm, 5.0*cm, 5.0*cm]
    t_res = Table(resumen_data, colWidths=col_w_res)
    t_res.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), _AZUL_OSCURO),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 8),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME",      (0, 1), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 1), (-1, 1), 11),
        ("TEXTCOLOR",     (1, 1), (1, 1), _VERDE),
        ("TEXTCOLOR",     (2, 1), (2, 1), _AZUL_MEDIO),
        ("GRID",          (0, 0), (-1, -1), 0.4, _GRIS_BORDE),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elementos.append(t_res)
    elementos.append(Spacer(1, 0.5 * cm))

    # ── Resumen agrupado por categoría (opcional) ─────────────────────────────
    if incluir_resumen_categorias and prods_filtrados:
        elementos.append(Paragraph(
            "<b>Resumen por Categoría</b>",
            ParagraphStyle("resumen_cat_titulo", fontName="Helvetica-Bold", fontSize=11,
                           textColor=_AZUL_OSCURO, spaceAfter=4),
        ))
        elementos.append(_tabla_inventario_general(prods_filtrados))
        elementos.append(Spacer(1, 0.5 * cm))

    # ── Tabla de productos ────────────────────────────────────────────────────
    if not prods_filtrados:
        elementos.append(Paragraph(
            "No hay productos para mostrar.",
            ParagraphStyle("vacio", fontName="Helvetica", fontSize=11,
                           textColor=colors.HexColor("#9CA3AF"), alignment=TA_CENTER),
        ))
    else:
        _estilo_prod_inv = ParagraphStyle(
            "prod_inv", fontName="Helvetica", fontSize=8,
            leading=10, wordWrap="CJK",
        )
        _estilo_prod_inv_bold = ParagraphStyle(
            "prod_inv_bold", fontName="Helvetica-Bold", fontSize=8,
            leading=10, wordWrap="CJK",
        )
        encabezado = [["#", "PRODUCTO", "SERIAL", "STOCK", "COSTO UNIT.", "VALOR TOTAL"]]
        filas = []
        _ORDEN_KEYS = {
            "categoria":  lambda x: (_categoria(x), x.producto.upper()),
            "stock_desc": lambda x: (-x.cantidad, x.producto.upper()),
            "stock_asc":  lambda x: (x.cantidad, x.producto.upper()),
        }
        prods_ord = sorted(prods_filtrados, key=_ORDEN_KEYS.get(orden, lambda x: x.producto.upper()))
        bajo_stock_rows: list[int] = []
        for i, p in enumerate(prods_ord, 1):
            valor_total = p.costo_unitario * p.cantidad
            bajo = (p.stock_minimo > 0 and p.cantidad < p.stock_minimo) or \
                   (p.stock_minimo == 0 and 0 < p.cantidad <= 2)
            if bajo:
                bajo_stock_rows.append(i)
            alerta = " (!)" if bajo else ""
            nombre_txt = (p.producto or "") + alerta
            estilo_p = _estilo_prod_inv_bold if bajo else _estilo_prod_inv
            filas.append([
                str(i),
                Paragraph(nombre_txt, estilo_p),
                p.serial or "—",
                str(p.cantidad),
                cop(p.costo_unitario),
                cop(valor_total),
            ])

        datos_tabla = encabezado + filas
        col_w_t = [0.7*cm, 7.2*cm, 1.8*cm, 1.4*cm, 2.8*cm, 2.9*cm]
        t = Table(datos_tabla, colWidths=col_w_t, repeatRows=1)
        n = len(datos_tabla)

        estilos_inv = [
            ("BACKGROUND",    (0, 0), (-1, 0), _AZUL_OSCURO),
            ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
            ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, 0), 7.5),
            ("ALIGN",         (0, 0), (-1, 0), "CENTER"),
            ("FONTSIZE",      (0, 1), (-1, -1), 8),
            ("ALIGN",         (0, 1), (0, -1), "CENTER"),
            ("ALIGN",         (3, 1), (3, -1), "CENTER"),
            ("ALIGN",         (4, 1), (-1, -1), "RIGHT"),
            ("FONTNAME",      (0, 1), (-1, -1), "Helvetica"),
            ("GRID",          (0, 0), (-1, -1), 0.4, _GRIS_BORDE),
            ("ROWBACKGROUNDS",(0, 1), (-1, n-1), [colors.white, _GRIS_CLARO]),
            ("TOPPADDING",    (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING",   (0, 1), (1, -1), 4),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ]
        for row_i in bajo_stock_rows:
            estilos_inv.append(("TEXTCOLOR", (3, row_i), (3, row_i), _ROJO))
            estilos_inv.append(("FONTNAME",  (3, row_i), (3, row_i), "Helvetica-Bold"))

        t.setStyle(TableStyle(estilos_inv))
        elementos.append(t)

    # ── Pie de página ─────────────────────────────────────────────────────────
    elementos.append(Spacer(1, 0.6 * cm))
    elementos.append(HRFlowable(width="100%", thickness=0.5, color=_GRIS_BORDE))
    elementos.append(Paragraph(
        f'{nombre_negocio}  •  Inventario generado el {ahora}',
        ParagraphStyle("pie", fontName="Helvetica", fontSize=7,
                       textColor=colors.HexColor("#9CA3AF"), alignment=TA_CENTER,
                       spaceBefore=4),
    ))

    doc.build(elementos)
