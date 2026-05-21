"""
services/pdf_reporte.py
Genera el reporte mensual en PDF usando reportlab.
Sin dependencias de UI.
"""

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


def generar_reporte_mensual_pdf(
    resumen: ResumenMensual,
    ventas,
    ruta: Path,
    nombre_negocio: str = "YJBMOTOCOM",
) -> None:
    """
    Genera un PDF con el reporte mensual completo.
    ventas: lista de objetos Venta del mes (para calcular comisiones por método).
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

    # ── 2. Tarjetas de resumen ────────────────────────────────────────────────
    elementos.append(_tabla_resumen(resumen))
    elementos.append(Spacer(1, 0.5 * cm))

    # ── 3. Comisiones por método ──────────────────────────────────────────────
    elementos.append(_titulo_seccion("Comisiones por Método de Pago", estilos))
    elementos.append(_tabla_comisiones(ventas, resumen))
    elementos.append(Spacer(1, 0.5 * cm))

    # ── 4. Resumen por día ────────────────────────────────────────────────────
    elementos.append(_titulo_seccion("Resumen por Día", estilos))
    elementos.append(_tabla_diaria(resumen))
    elementos.append(Spacer(1, 0.5 * cm))

    # ── 5. Pie de página ──────────────────────────────────────────────────────
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
        # Fila 1
        ["VENTAS DEL MES", "INGRESOS TOTALES", "GANANCIA NETA", "UTILIDAD REAL"],
        [
            str(resumen.cantidad_ventas),
            cop(resumen.total_ingresos),
            cop(resumen.ganancia_neta),
            cop(resumen.utilidad_real),
        ],
        # Fila 2: subtítulos
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
        # Encabezados
        ("BACKGROUND",   (0, 0), (-1, 0), _AZUL_OSCURO),
        ("TEXTCOLOR",    (0, 0), (-1, 0), colors.white),
        ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, 0), 7.5),
        ("ALIGN",        (0, 0), (-1, 0), "CENTER"),
        ("BOTTOMPADDING",(0, 0), (-1, 0), 4),
        ("TOPPADDING",   (0, 0), (-1, 0), 5),
        # Valores grandes
        ("FONTNAME",     (0, 1), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 1), (-1, 1), 14),
        ("ALIGN",        (0, 1), (-1, 1), "CENTER"),
        ("TEXTCOLOR",    (0, 1), (0,  1), _AZUL_MEDIO),
        ("TEXTCOLOR",    (1, 1), (1,  1), _AZUL_OSCURO),
        ("TEXTCOLOR",    (2, 1), (2,  1), _VERDE if resumen.ganancia_neta >= 0 else _ROJO),
        ("TEXTCOLOR",    (3, 1), (3,  1), color_util),
        ("BACKGROUND",   (3, 0), (3, -1), fondo_util),
        # UTILIDAD REAL: mayor tamaño y padding para destacar
        ("FONTSIZE",     (3, 1), (3,  1), 17),
        ("TOPPADDING",   (3, 1), (3,  1), 8),
        ("BOTTOMPADDING",(3, 1), (3,  1), 8),
        ("BOTTOMPADDING",(0, 1), (-1, 1), 4),
        ("TOPPADDING",   (0, 1), (-1, 1), 6),
        # Subtítulos
        ("FONTSIZE",     (0, 2), (-1, 2), 8),
        ("TEXTCOLOR",    (0, 2), (-1, 2), _GRIS_TEXTO),
        ("ALIGN",        (0, 2), (-1, 2), "CENTER"),
        ("BOTTOMPADDING",(0, 2), (-1, 2), 6),
        # Bordes
        ("GRID",         (0, 0), (-1, -1), 0.5, _GRIS_BORDE),
        ("ROUNDEDCORNERS", [4]),
    ]))
    return t


def _tabla_comisiones(ventas, resumen: ResumenMensual) -> Table:
    # Agrupar comisiones por método
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
            ("ALIGN",     (0, 0), (-1, -1), "CENTER"),
            ("TEXTCOLOR", (0, 0), (-1, -1), _GRIS_TEXTO),
            ("FONTSIZE",  (0, 0), (-1, -1), 9),
            ("TOPPADDING",(0, 0), (-1, -1), 8),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 8),
        ]))
        return t

    encabezado = [["MÉTODO", "VENTAS CON COMISIÓN", "TOTAL COMISIÓN"]]
    filas = [
        [metodo, str(conteo[metodo]), cop(monto)]
        for metodo, monto in sorted(totales.items(), key=lambda x: -x[1])
    ]
    # Totales
    filas.append(["TOTAL", str(sum(conteo.values())), cop(resumen.total_comisiones)])

    datos = encabezado + filas
    col_w = [6 * cm, 5.5 * cm, 5.8 * cm]
    t = Table(datos, colWidths=col_w)
    n = len(datos)
    t.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0), _AZUL_OSCURO),
        ("TEXTCOLOR",    (0, 0), (-1, 0), colors.white),
        ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, 0), 8),
        ("ALIGN",        (0, 0), (-1, 0), "CENTER"),
        ("FONTSIZE",     (0, 1), (-1, -2), 9),
        ("ALIGN",        (1, 1), (-1, -1), "CENTER"),
        # Fila de totales
        ("BACKGROUND",   (0, n-1), (-1, n-1), _GRIS_CLARO),
        ("FONTNAME",     (0, n-1), (-1, n-1), "Helvetica-Bold"),
        ("TEXTCOLOR",    (2, 1), (2, n-2), _ROJO),
        ("TEXTCOLOR",    (2, n-1), (2, n-1), _ROJO),
        ("GRID",         (0, 0), (-1, -1), 0.5, _GRIS_BORDE),
        ("ROWBACKGROUNDS",(0, 1), (-1, n-2), [colors.white, _GRIS_CLARO]),
        ("TOPPADDING",   (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
    ]))
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
        ("BACKGROUND",   (0, 0), (-1, 0), _AZUL_OSCURO),
        ("TEXTCOLOR",    (0, 0), (-1, 0), colors.white),
        ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, 0), 7.5),
        ("ALIGN",        (0, 0), (-1, 0), "CENTER"),
        ("FONTSIZE",     (0, 1), (-1, -1), 8),
        ("ALIGN",        (0, 1), (1, -1), "CENTER"),
        ("ALIGN",        (2, 1), (5, -1), "RIGHT"),
        ("ALIGN",        (6, 1), (6, -1), "CENTER"),
        ("GRID",         (0, 0), (-1, -1), 0.4, _GRIS_BORDE),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, _GRIS_CLARO]),
        ("TOPPADDING",   (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
    ]

    # Colorear utilidad y estado fila por fila
    for i, rd in enumerate(resumen.resumen_por_dia, start=1):
        color_util = _VERDE if rd.utilidad_real >= 0 else _ROJO
        color_est  = _VERDE if rd.es_positivo     else _ROJO
        estilos_tabla.append(("TEXTCOLOR", (5, i), (5, i), color_util))
        estilos_tabla.append(("TEXTCOLOR", (6, i), (6, i), color_est))

    t.setStyle(TableStyle(estilos_tabla))
    return t
