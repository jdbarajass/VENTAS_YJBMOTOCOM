"""
ui/styles.py
Sistema de diseño global — aplicado una vez en main.py via app.setStyleSheet().
Inspiración: Notion / Stripe / Linear.

Tokens de diseño:
  Primario   : #2563EB  (azul)
  Éxito      : #16A34A  (verde)
  Peligro    : #DC2626  (rojo)
  Advertencia: #D97706  (ámbar)
  Fondo app  : #F1F5F9  (gris-azul muy claro)
  Superficie : #FFFFFF  (blanco)
  Borde      : #E5E7EB  (gris claro)
  Texto prim : #111827  (casi negro)
  Texto sec  : #6B7280  (gris)
  Texto muted: #9CA3AF  (gris claro)
"""


GLOBAL_STYLESHEET = """

/* ==========================================================
   BASE — Tipografía y fondo de aplicación
   ========================================================== */

QMainWindow, QDialog {
    background-color: #F1F5F9;
}

QWidget {
    font-family: "Segoe UI", "Arial", sans-serif;
    font-size: 13px;
    color: #111827;
}

QLabel {
    background: transparent;
}

/* ==========================================================
   INPUTS — Campos de texto, combos, spinboxes
   ========================================================== */

QLineEdit {
    border: 1px solid #D1D5DB;
    border-radius: 6px;
    padding: 5px 10px;
    background: #FFFFFF;
    color: #111827;
    selection-background-color: #DBEAFE;
    selection-color: #1D4ED8;
}
QLineEdit:focus {
    border: 2px solid #2563EB;
    padding: 4px 9px;
}
QLineEdit:disabled {
    background: #F9FAFB;
    color: #9CA3AF;
    border-color: #E5E7EB;
}
QLineEdit:hover:!focus {
    border-color: #9CA3AF;
}

QTextEdit, QPlainTextEdit {
    border: 1px solid #D1D5DB;
    border-radius: 6px;
    padding: 6px 10px;
    background: #FFFFFF;
    selection-background-color: #DBEAFE;
}
QTextEdit:focus, QPlainTextEdit:focus {
    border: 2px solid #2563EB;
}

QComboBox {
    border: 1px solid #D1D5DB;
    border-radius: 6px;
    padding: 5px 10px;
    background: #FFFFFF;
    color: #111827;
}
QComboBox:focus {
    border: 2px solid #2563EB;
}
QComboBox:hover:!focus {
    border-color: #9CA3AF;
}
QComboBox::drop-down {
    border: none;
    width: 28px;
}
QComboBox QAbstractItemView {
    border: 1px solid #E5E7EB;
    border-radius: 6px;
    background: #FFFFFF;
    padding: 2px;
    selection-background-color: #EFF6FF;
    selection-color: #1D4ED8;
    outline: none;
}
QComboBox QAbstractItemView::item {
    padding: 6px 10px;
    border-radius: 4px;
}

QSpinBox, QDoubleSpinBox {
    border: 1px solid #D1D5DB;
    border-radius: 6px;
    padding: 5px 10px;
    background: #FFFFFF;
    color: #111827;
}
QSpinBox:focus, QDoubleSpinBox:focus {
    border: 2px solid #2563EB;
}
QSpinBox:hover:!focus, QDoubleSpinBox:hover:!focus {
    border-color: #9CA3AF;
}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
    width: 18px;
    border: none;
    background: transparent;
}

QDateEdit {
    border: 1px solid #D1D5DB;
    border-radius: 6px;
    padding: 5px 10px;
    background: #FFFFFF;
}
QDateEdit:focus {
    border: 2px solid #2563EB;
}
QDateEdit::drop-down {
    border: none;
    width: 24px;
}

/* ==========================================================
   BOTONES — Estado base / hover / pressed / disabled
   ========================================================== */

QPushButton {
    border: 1px solid #D1D5DB;
    border-radius: 6px;
    padding: 6px 16px;
    background: #FFFFFF;
    color: #374151;
    font-weight: 500;
}
QPushButton:hover {
    background: #F9FAFB;
    border-color: #9CA3AF;
}
QPushButton:pressed {
    background: #F3F4F6;
}
QPushButton:disabled {
    background: #F9FAFB;
    color: #9CA3AF;
    border-color: #E5E7EB;
}
QPushButton:flat {
    border: none;
    background: transparent;
}

/* ==========================================================
   TABLAS
   ========================================================== */

QTableWidget {
    border: none;
    background: #FFFFFF;
    gridline-color: #F1F5F9;
    alternate-background-color: #F8FAFC;
    selection-background-color: #DBEAFE;
    selection-color: #1E3A5F;
    outline: none;
}
QTableWidget::item {
    padding: 4px 8px;
    border: none;
}
QTableWidget::item:selected {
    background: #DBEAFE;
    color: #1E3A5F;
}
QHeaderView::section {
    background: #1E293B;
    color: #F8FAFC;
    padding: 7px 10px;
    border: none;
    font-weight: bold;
    font-size: 11px;
    letter-spacing: 0.3px;
}
QHeaderView::section:horizontal:hover {
    background: #334155;
}

/* ==========================================================
   SCROLLBARS — Delgadas, estilo moderno
   ========================================================== */

QScrollBar:vertical {
    border: none;
    background: transparent;
    width: 7px;
    margin: 2px 1px;
}
QScrollBar::handle:vertical {
    background: #CBD5E1;
    border-radius: 3px;
    min-height: 28px;
}
QScrollBar::handle:vertical:hover {
    background: #94A3B8;
}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background: none;
}

QScrollBar:horizontal {
    border: none;
    background: transparent;
    height: 7px;
    margin: 1px 2px;
}
QScrollBar::handle:horizontal {
    background: #CBD5E1;
    border-radius: 3px;
    min-width: 28px;
}
QScrollBar::handle:horizontal:hover {
    background: #94A3B8;
}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* ==========================================================
   GROUPBOX
   ========================================================== */

QGroupBox {
    font-weight: bold;
    font-size: 13px;
    color: #374151;
    border: 1px solid #E5E7EB;
    border-radius: 10px;
    margin-top: 16px;
    padding: 16px 12px 12px 12px;
    background: #FFFFFF;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    background: #FFFFFF;
    color: #374151;
}

/* ==========================================================
   DIALOGS / MESSAGEBOX
   ========================================================== */

QDialog {
    background: #FFFFFF;
}
QMessageBox {
    background: #FFFFFF;
}
QMessageBox QPushButton {
    min-width: 80px;
    padding: 6px 20px;
}

/* ==========================================================
   CALENDARIO POPUP
   ========================================================== */

QCalendarWidget {
    background: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 8px;
}
QCalendarWidget QToolButton {
    color: #374151;
    background: transparent;
    border: none;
    border-radius: 4px;
    padding: 4px 8px;
    font-weight: bold;
}
QCalendarWidget QToolButton:hover {
    background: #F3F4F6;
}
QCalendarWidget QAbstractItemView {
    selection-background-color: #2563EB;
    selection-color: #FFFFFF;
    color: #374151;
    gridline-color: #F1F5F9;
}
QCalendarWidget QWidget#qt_calendar_navigationbar {
    background: #1E293B;
    border-radius: 6px 6px 0 0;
    padding: 4px;
}
QCalendarWidget QToolButton#qt_calendar_prevmonth,
QCalendarWidget QToolButton#qt_calendar_nextmonth {
    color: #F8FAFC;
}
QCalendarWidget QSpinBox {
    color: #F8FAFC;
    background: transparent;
    border: none;
    font-weight: bold;
}

/* ==========================================================
   TOOLTIP
   ========================================================== */

QToolTip {
    background: #1E293B;
    color: #F8FAFC;
    border: none;
    padding: 5px 9px;
    border-radius: 5px;
    font-size: 11px;
}

/* ==========================================================
   STATUS BAR
   ========================================================== */

QStatusBar {
    background: #1E293B;
    color: #94A3B8;
    font-size: 11px;
    border-top: 1px solid #334155;
}
QStatusBar::item {
    border: none;
}

/* ==========================================================
   SCROLL AREA
   ========================================================== */

QScrollArea {
    border: none;
    background: transparent;
}
QScrollArea > QWidget > QWidget {
    background: transparent;
}

/* ==========================================================
   SEPARADORES
   ========================================================== */

QFrame[frameShape="4"],
QFrame[frameShape="5"] {
    color: #E5E7EB;
}

"""


def aplicar_sombra(widget, radio: int = 12, opacidad: int = 18,
                   dx: int = 0, dy: int = 2) -> None:
    """
    Aplica QGraphicsDropShadowEffect a un widget para simular elevación.
    Usar con moderación — solo en tarjetas principales.
    """
    from PySide6.QtWidgets import QGraphicsDropShadowEffect
    from PySide6.QtGui import QColor

    sombra = QGraphicsDropShadowEffect(widget)
    sombra.setBlurRadius(radio)
    sombra.setColor(QColor(0, 0, 0, opacidad))
    sombra.setOffset(dx, dy)
    widget.setGraphicsEffect(sombra)
