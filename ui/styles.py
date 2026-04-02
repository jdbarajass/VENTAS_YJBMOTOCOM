"""
Estilos y temas para la interfaz gráfica.
Define colores, fuentes y estilos CSS para PySide6.
"""

# Paleta de colores
COLORS = {
    "primary": "#2c3e50",       # Azul oscuro - color principal
    "secondary": "#3498db",     # Azul claro - acentos
    "success": "#27ae60",       # Verde - positivo/ganancia
    "danger": "#e74c3c",        # Rojo - negativo/pérdida
    "warning": "#f39c12",       # Naranja - advertencia
    "info": "#17a2b8",          # Cyan - información
    "light": "#f5f6fa",         # Gris muy claro - fondo
    "dark": "#2c3e50",          # Gris oscuro - texto
    "white": "#ffffff",         # Blanco
    "border": "#dcdde1",        # Gris claro - bordes
    "text": "#2c3e50",          # Texto principal
    "text_secondary": "#7f8c8d", # Texto secundario
    "card_bg": "#ffffff",       # Fondo de tarjetas
}

# Estilos CSS globales para la aplicación
STYLESHEET = """
/* ============================================
   ESTILOS GLOBALES
   ============================================ */

QMainWindow {
    background-color: #f5f6fa;
}

QWidget {
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
    color: #2c3e50;
}

/* ============================================
   TABS (PESTAÑAS)
   ============================================ */

QTabWidget::pane {
    border: 1px solid #dcdde1;
    background-color: #ffffff;
    border-radius: 8px;
    margin-top: -1px;
}

QTabBar::tab {
    background-color: #ecf0f1;
    color: #7f8c8d;
    padding: 12px 24px;
    margin-right: 4px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    font-weight: bold;
    min-width: 120px;
}

QTabBar::tab:selected {
    background-color: #ffffff;
    color: #2c3e50;
    border: 1px solid #dcdde1;
    border-bottom: none;
}

QTabBar::tab:hover:!selected {
    background-color: #dcdde1;
}

/* ============================================
   BOTONES
   ============================================ */

QPushButton {
    background-color: #3498db;
    color: white;
    border: none;
    padding: 10px 20px;
    border-radius: 6px;
    font-weight: bold;
    min-width: 100px;
}

QPushButton:hover {
    background-color: #2980b9;
}

QPushButton:pressed {
    background-color: #1f6dad;
}

QPushButton:disabled {
    background-color: #bdc3c7;
    color: #7f8c8d;
}

QPushButton#btnRegistrar {
    background-color: #27ae60;
    font-size: 14px;
    padding: 12px 30px;
}

QPushButton#btnRegistrar:hover {
    background-color: #219a52;
}

QPushButton#btnExportar {
    background-color: #2c3e50;
}

QPushButton#btnExportar:hover {
    background-color: #1a252f;
}

QPushButton#btnEliminar {
    background-color: #e74c3c;
    min-width: 80px;
    padding: 6px 12px;
}

QPushButton#btnEliminar:hover {
    background-color: #c0392b;
}

/* ============================================
   CAMPOS DE ENTRADA
   ============================================ */

QLineEdit, QSpinBox, QDoubleSpinBox {
    padding: 10px 12px;
    border: 2px solid #dcdde1;
    border-radius: 6px;
    background-color: white;
    font-size: 13px;
}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #3498db;
}

QLineEdit:disabled {
    background-color: #ecf0f1;
    color: #7f8c8d;
}

QTextEdit {
    padding: 10px;
    border: 2px solid #dcdde1;
    border-radius: 6px;
    background-color: white;
}

QTextEdit:focus {
    border-color: #3498db;
}

/* ============================================
   COMBO BOX Y DATE EDIT
   ============================================ */

QComboBox {
    padding: 10px 12px;
    border: 2px solid #dcdde1;
    border-radius: 6px;
    background-color: white;
    min-width: 150px;
}

QComboBox:focus {
    border-color: #3498db;
}

QComboBox::drop-down {
    border: none;
    width: 30px;
}

QComboBox::down-arrow {
    width: 12px;
    height: 12px;
}

QComboBox QAbstractItemView {
    border: 1px solid #dcdde1;
    background-color: white;
    selection-background-color: #3498db;
    selection-color: white;
}

QDateEdit {
    padding: 10px 12px;
    border: 2px solid #dcdde1;
    border-radius: 6px;
    background-color: white;
}

QDateEdit:focus {
    border-color: #3498db;
}

QDateEdit::drop-down {
    border: none;
    width: 30px;
}

/* ============================================
   TABLAS
   ============================================ */

QTableWidget {
    border: 1px solid #dcdde1;
    border-radius: 8px;
    background-color: white;
    gridline-color: #ecf0f1;
    selection-background-color: #3498db;
    selection-color: white;
}

QTableWidget::item {
    padding: 8px;
    border-bottom: 1px solid #ecf0f1;
}

QTableWidget::item:selected {
    background-color: #3498db;
    color: white;
}

QHeaderView::section {
    background-color: #2c3e50;
    color: white;
    padding: 12px 8px;
    border: none;
    font-weight: bold;
}

QHeaderView::section:first {
    border-top-left-radius: 8px;
}

QHeaderView::section:last {
    border-top-right-radius: 8px;
}

/* ============================================
   ETIQUETAS
   ============================================ */

QLabel {
    color: #2c3e50;
}

QLabel#lblTitulo {
    font-size: 24px;
    font-weight: bold;
    color: #2c3e50;
    padding: 10px 0;
}

QLabel#lblSubtitulo {
    font-size: 16px;
    color: #7f8c8d;
    padding: 5px 0;
}

/* ============================================
   RADIO BUTTONS
   ============================================ */

QRadioButton {
    spacing: 8px;
    font-size: 13px;
}

QRadioButton::indicator {
    width: 18px;
    height: 18px;
}

QRadioButton::indicator:checked {
    background-color: #3498db;
    border: 2px solid #3498db;
    border-radius: 10px;
}

QRadioButton::indicator:unchecked {
    background-color: white;
    border: 2px solid #dcdde1;
    border-radius: 10px;
}

/* ============================================
   GROUP BOX
   ============================================ */

QGroupBox {
    font-weight: bold;
    border: 2px solid #dcdde1;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 10px;
    background-color: white;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 15px;
    padding: 0 10px;
    color: #2c3e50;
}

/* ============================================
   SCROLL BARS
   ============================================ */

QScrollBar:vertical {
    background-color: #f5f6fa;
    width: 12px;
    border-radius: 6px;
}

QScrollBar::handle:vertical {
    background-color: #bdc3c7;
    border-radius: 6px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background-color: #95a5a6;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background-color: #f5f6fa;
    height: 12px;
    border-radius: 6px;
}

QScrollBar::handle:horizontal {
    background-color: #bdc3c7;
    border-radius: 6px;
    min-width: 30px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #95a5a6;
}

/* ============================================
   FRAMES Y CONTENEDORES
   ============================================ */

QFrame#cardFrame {
    background-color: white;
    border: 1px solid #dcdde1;
    border-radius: 10px;
    padding: 15px;
}

QFrame#dashboardCard {
    background-color: white;
    border: 1px solid #dcdde1;
    border-radius: 10px;
}

QFrame#cardPositivo {
    background-color: #d5f4e6;
    border: 2px solid #27ae60;
    border-radius: 10px;
}

QFrame#cardNegativo {
    background-color: #fadbd8;
    border: 2px solid #e74c3c;
    border-radius: 10px;
}

/* ============================================
   MENSAJES Y ALERTAS
   ============================================ */

QMessageBox {
    background-color: white;
}

QMessageBox QPushButton {
    min-width: 80px;
    padding: 8px 16px;
}

/* ============================================
   TOOLTIPS
   ============================================ */

QToolTip {
    background-color: #2c3e50;
    color: white;
    border: none;
    padding: 8px 12px;
    border-radius: 4px;
    font-size: 12px;
}
"""


def get_card_style(tipo: str = "normal") -> str:
    """
    Retorna el estilo CSS para una tarjeta según el tipo.

    Args:
        tipo: 'normal', 'positivo', 'negativo', 'warning'

    Returns:
        String con el estilo CSS
    """
    estilos = {
        "normal": """
            background-color: #ffffff;
            border: 1px solid #dcdde1;
            border-radius: 10px;
            padding: 15px;
        """,
        "positivo": """
            background-color: #d5f4e6;
            border: 2px solid #27ae60;
            border-radius: 10px;
            padding: 15px;
        """,
        "negativo": """
            background-color: #fadbd8;
            border: 2px solid #e74c3c;
            border-radius: 10px;
            padding: 15px;
        """,
        "warning": """
            background-color: #fef9e7;
            border: 2px solid #f39c12;
            border-radius: 10px;
            padding: 15px;
        """,
        "info": """
            background-color: #ebf5fb;
            border: 2px solid #3498db;
            border-radius: 10px;
            padding: 15px;
        """
    }
    return estilos.get(tipo, estilos["normal"])


def get_value_label_style(tipo: str = "normal") -> str:
    """
    Retorna el estilo CSS para etiquetas de valor.

    Args:
        tipo: 'normal', 'positivo', 'negativo', 'grande'

    Returns:
        String con el estilo CSS
    """
    estilos = {
        "normal": "font-size: 18px; font-weight: bold; color: #2c3e50;",
        "positivo": "font-size: 18px; font-weight: bold; color: #27ae60;",
        "negativo": "font-size: 18px; font-weight: bold; color: #e74c3c;",
        "grande": "font-size: 24px; font-weight: bold; color: #2c3e50;",
        "grande_positivo": "font-size: 24px; font-weight: bold; color: #27ae60;",
        "grande_negativo": "font-size: 24px; font-weight: bold; color: #e74c3c;",
    }
    return estilos.get(tipo, estilos["normal"])
