# YJBMOTOCOM — Control de Rentabilidad

Aplicación de escritorio para gestión integral de un negocio de motocicletas: ventas, inventario, facturas, gastos, préstamos, presupuesto y reportes. Construida con Python y PySide6 (Qt6), base de datos SQLite embebida, compilable a `.exe` con PyInstaller.

---

## Funcionalidades principales

| Módulo | Descripción |
|--------|-------------|
| **Registrar Venta** | Carrito multi-ítem, escaneo de código de barras, pagos combinados (efectivo + Bold + Addi + Transferencia), descuento automático de inventario |
| **Dashboard** | Resumen diario de ganancias, gráfica de tendencia últimos 7 días, desglose de comisiones por método de pago |
| **Historial Mensual** | Filtro por mes o rango libre de fechas, chips de comisiones acumuladas, exportar a PDF o imprimir |
| **Inventario** | CRUD de productos con serial, costo, cantidad y código de barras; alertas de stock bajo (≤ 2 ud.) |
| **Facturas** | Control de facturas a proveedores, abonos parciales, alertas de vencimiento ≤ 7 días |
| **Préstamos** | Seguimiento de productos prestados a almacenes externos |
| **Presupuesto Mensual** | Comparativo presupuesto vs. gasto real por categoría |
| **Notas y Pendientes** | Tareas con fecha límite, badge de vencidas en sidebar |
| **Cuentas** | Control de saldo por medio de pago (Efectivo, Nequi, QR, NU, Daviplata, Addi), transferencias entre cuentas, historial de movimientos y cierres mensuales — solo Admin |
| **Exportar / Importar** | Backup a Excel multi-hoja (protegido con contraseña) e importación con validación de coherencia |
| **Calculadora** | Cálculo instantáneo de precio de venta, margen y comisión |
| **Configuración** | Gastos fijos, comisiones, impresora térmica, seguridad, usuarios, auditoría, apariencia |
| **Multi-usuario** | Login con tarjetas, roles Admin / Vendedor, cierre de sesión sin reiniciar |

---

## Stack técnico

| Componente | Tecnología |
|------------|------------|
| Lenguaje | Python 3.11+ |
| GUI | PySide6 (Qt 6) |
| Base de datos | SQLite (WAL mode, foreign keys, singleton de conexión) |
| Excel | openpyxl ≥ 3.1 |
| PDF | reportlab ≥ 4.0 |
| Impresora térmica | python-escpos ≥ 3.1 |
| Empaquetado | PyInstaller ≥ 6.3 (`--onedir`, `--windowed`) |
| Tests | pytest (30 tests automáticos) |

---

## Arquitectura

El proyecto sigue una arquitectura en capas estricta:

```
BD (SQLite)
  └── database/          ← Repositorios: acceso directo a tablas
        └── connection.py, schema.py, *_repo.py
  └── models/            ← Dataclasses puros, sin lógica de BD
controllers/             ← Casos de uso: orquestan repos y validan
services/                ← Servicios transversales (PDF, Excel, ESC/POS, cálculos)
ui/                      ← Vistas PySide6: solo presentación, sin lógica de negocio
utils/                   ← Herramientas globales (logger, security, auditoria, backup)
main.py                  ← Punto de entrada: inicializa Qt, BD, login, MainWindow
```

### Reglas de dependencia
- `ui/` importa de `controllers/`, `models/` y `services/` — nunca de `database/` directamente.
- `controllers/` importa de `database/` y `models/`.
- `database/` importa de `models/`.
- `utils/` no importa de ninguna otra capa del proyecto.

---

## Estructura de módulos

```
VENTAS_YJBMOTOCOM/
├── main.py                        # Punto de entrada
├── build.bat                      # Script para generar el .exe
├── requirements.txt               # Dependencias pip
│
├── assets/                        # Personalización visual (opcional)
│   ├── icon.ico / icon.png        # Icono de ventana y taskbar
│   └── logo.png / *.png           # Logo del sidebar (cualquier PNG/JPG)
│
├── models/                        # Modelos de dominio (dataclasses)
│   ├── venta.py
│   ├── gasto_dia.py
│   ├── factura.py, abono_factura.py
│   ├── producto.py, prestamo.py
│   ├── nota.py
│   ├── cuenta.py                  # Cuenta, MovimientoCuenta, CierreMensual
│   └── configuracion.py
│
├── database/                      # Acceso a BD
│   ├── connection.py              # Singleton DatabaseConnection (WAL + FK)
│   ├── schema.py                  # Creación de tablas + 14 migraciones versionadas
│   ├── ventas_repo.py
│   ├── gastos_dia_repo.py
│   ├── facturas_repo.py, abonos_factura_repo.py
│   ├── inventario_repo.py, prestamos_repo.py
│   ├── notas_repo.py, presupuesto_repo.py
│   ├── usuarios_repo.py           # Multi-usuario
│   ├── cuentas_repo.py            # Saldos, movimientos y cierres de Cuentas
│   └── config_repo.py
│
├── controllers/
│   ├── venta_controller.py        # Registra venta + descuenta inventario + acredita cuentas
│   ├── historial_controller.py
│   ├── dashboard_controller.py
│   ├── facturas_controller.py
│   ├── prestamos_controller.py
│   ├── ventas_dia_controller.py
│   └── config_controller.py
│
├── services/
│   ├── calculator.py              # Cálculo de comisiones y ganancia neta
│   ├── reportes.py                # Agregaciones mensuales
│   ├── exportador.py              # Excel multi-hoja con protección de contraseña
│   ├── importador.py              # Importación con validación de coherencia
│   ├── inventario_importador.py
│   ├── pdf_reporte.py             # Reportes PDF con reportlab
│   ├── recibo_generator.py        # Recibos de venta (PDF / ESC/POS)
│   ├── escpos_printer.py          # Impresora térmica ESC/POS
│   ├── pdf_distrifabrica_parser.py
│   └── pdf_pedido_parser.py
│
├── ui/                            # Vistas PySide6
│   ├── main_window.py             # Shell: sidebar + QStackedWidget
│   ├── styles.py                  # GLOBAL_STYLESHEET + DARK_STYLESHEET + aplicar_tema()
│   ├── login_dialog.py            # Login con tarjetas de usuario
│   ├── busqueda_widget.py         # Búsqueda global con debounce 250ms
│   ├── venta_form.py              # Formulario de venta (carrito + scan de barcode)
│   ├── dashboard_panel.py         # Dashboard + _TendenciaWidget (QPainter)
│   ├── historial_panel.py         # Historial con filtro de rango y export PDF
│   ├── config_panel.py            # Configuración + usuarios + auditoría + apariencia
│   ├── inventario_panel.py
│   ├── facturas_panel.py
│   ├── prestamos_panel.py
│   ├── notas_panel.py
│   ├── presupuesto_panel.py
│   ├── exportar_importar_panel.py
│   ├── calculadora_panel.py
│   ├── cuentas_panel.py           # Panel Cuentas (3 tabs: Resumen, Movimientos, Cierres)
│   └── ventas_dia_panel.py
│
├── utils/
│   ├── security.py                # SHA-256: hashear_clave(), verificar_clave(), es_hash()
│   ├── logger.py                  # Logger a errors.log + consola
│   ├── auditoria.py               # Registro de acciones (log_acciones) por usuario
│   ├── backup.py                  # Backup automático al arrancar (hasta 7 copias)
│   ├── formatters.py              # cop(), porcentaje(), etc.
│   ├── pdf_utils.py
│   └── busy.py                    # Cursor de espera
│
└── tests/
    ├── test_security.py           # 12 tests: hash, verificación, legacy
    ├── test_calculator.py         # 14 tests: comisiones, ganancias, utilidad
    └── test_schema_migrations.py  # 4 tests: migrations idempotentes, schema_version
```

---

## Instalación y ejecución en desarrollo

```bash
# 1. Clonar el repositorio
git clone https://github.com/jdbarajass/VENTAS_YJBMOTOCOM.git
cd VENTAS_YJBMOTOCOM

# 2. Crear entorno virtual (recomendado)
python -m venv .venv
.venv\Scripts\activate       # Windows
# source .venv/bin/activate  # Linux/Mac

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Ejecutar
python main.py
```

La base de datos `ventas.db` se crea automáticamente en el mismo directorio en el primer arranque.

### Ejecutar tests

```bash
python -m pytest tests/ -v
# 30 tests — deben pasar todos en < 1 segundo
```

---

## Compilar a ejecutable (.exe)

```batch
build.bat
```

Genera `dist\YJBMOTOCOM\YJBMOTOCOM.exe` (carpeta auto-contenida, sin Python instalado).  
Para distribuir: copiar toda la carpeta `dist\YJBMOTOCOM\` y crear un acceso directo al `.exe`.

> **Nota:** La base de datos `ventas.db` y los backups se almacenan junto al `.exe` en producción.

---

## Personalización visual — Logo e icono

El programa detecta automáticamente los archivos en la carpeta `assets/` al arrancar, sin necesidad de recompilar.

| Archivo | Efecto | Formato recomendado |
|---------|--------|---------------------|
| `assets/icon.ico` | Icono de la ventana y de la taskbar de Windows | `.ico` 256×256 px (o multi-resolución) |
| `assets/icon.png` | Alternativa si no se dispone de `.ico` | PNG cuadrado ≥ 64×64 px |
| `assets/logo.png` _(o cualquier PNG/JPG)_ | Imagen en el sidebar, reemplaza el texto "YJBMOTOCOM" | PNG con fondo transparente u oscuro, ~180 px de ancho |

**Regla de búsqueda del logo:** el programa busca primero `logo.png` / `logo.jpg` / `logo.jpeg`; si no existe ninguno, usa el primer PNG o JPG que encuentre en `assets/` (excluyendo el archivo `icon.*`).

**Para el build `.exe`:** si existe `assets/icon.ico`, se incrusta automáticamente como icono del ejecutable. La carpeta `assets/` completa se incluye en el bundle.

---

## Seguridad

### Contraseña de acceso
- Se almacena como **SHA-256 hex** (64 caracteres) en la tabla `configuracion`.
- Al arrancar, si detecta una contraseña en texto plano (versión anterior), la convierte automáticamente al hash.
- Contraseña por defecto: `YJB2026_*`

### Páginas protegidas
Las páginas **Configuración**, **Exportar/Importar** y **Cuentas** requieren contraseña para acceder. La sesión desbloquea la página hasta que:
- El timer de inactividad expira (configurable, por defecto 10 min).
- El usuario cierra sesión manualmente.

### Roles
| Rol | Acceso |
|-----|--------|
| **Admin** | Todo, incluyendo Configuración, Exportar/Importar y Cuentas |
| **Vendedor** | Todo excepto Configuración, Exportar/Importar y Cuentas; el Dashboard muestra una vista resumida sin datos financieros (costos, comisiones, márgenes, utilidad real) |

### Excel exportado
Las hojas **Inventario** y **Configuración** del Excel exportado quedan protegidas con contraseña de worksheet (solo lectura).

---

## Base de datos — Migraciones

El sistema de migraciones es **forward-only e idempotente** (seguro de ejecutar en cada arranque):

| Versión | Descripción |
|---------|-------------|
| 1 | cantidad, pagos_combinados, grupo_venta_id en ventas |
| 2 | numero_factura en ventas |
| 3 | fecha_vencimiento, fecha_pago en facturas |
| 4 | categoria en gastos_dia |
| 5 | clave_inventario en configuracion |
| 6 | nombre_impresora en configuracion |
| 7 | hora en prestamos |
| 8 | fecha_limite en notas |
| 9 | CREATE TABLE log_acciones (auditoría) |
| 10 | CREATE TABLE usuarios (multi-usuario) |
| 11 | modo_oscuro en configuracion |
| 12 | timeout_minutos en configuracion |
| 13 | hora en ventas (análisis de horas pico) |
| 14 | CREATE TABLE cuentas, cuentas_movimientos, cuentas_cierres + seed de 6 cuentas por defecto |
| 15–25 | Gastos con cuenta de débito, comisiones por cuenta (Nequi/NU/QR/Daviplata/Datafono), stock_minimo y categoria en inventario, historial de movimientos de inventario, productos vinculados a facturas (`facturas_items`), precio_ofertado en ventas, cuenta_id en facturas/abonos |
| 26 | talla en inventario (antes inferida del nombre del producto vía regex `-T:`) + backfill automático que migra la talla embebida y limpia el nombre |
| 27 | backup_automatico_activo, backup_intervalo_horas en configuracion (backup programado mientras la app está abierta) |

La tabla `schema_version` registra qué migraciones ya se aplicaron. Al actualizar el `.exe` en producción, solo se aplican las versiones nuevas.

---

## Historial de mejoras

### Fase 1 — Seguridad ✅
| # | Mejora |
|---|--------|
| 1.1 | Hash SHA-256 para la contraseña (ya no se guarda en texto plano) |
| 1.2 | Migración automática plain-text → hash al arrancar |
| 1.3 | Timeout de sesión: bloqueo automático tras N minutos de inactividad |
| 1.4 | Protección con contraseña en hojas Excel exportadas |
| 1.5 | Panel Exportar/Importar protegido por contraseña |

### Fase 2 — Estabilidad y Mantenimiento ✅
| # | Mejora |
|---|--------|
| 2.1 | Log de errores a archivo `errors.log` |
| 2.2 | Migraciones de BD versionadas (tabla `schema_version`, 12 versiones) |
| 2.3 | 30 tests automáticos: security, calculator, migraciones |

### Fase 3 — Alertas y Búsqueda ✅
| # | Mejora |
|---|--------|
| 3.1 | Alerta al arrancar + badge en sidebar si hay facturas venciendo ≤ 7 días |
| 3.2 | Búsqueda global en sidebar: inventario, facturas, ventas con debounce 250ms |
| 3.3 | Notas con fecha límite, badge de vencidas en sidebar, diálogo mejorado |

### Fase 4 — Reportes y Exportación ✅
| # | Mejora |
|---|--------|
| 4.1 | Exportar reporte mensual a PDF con reportlab |
| 4.2 | Resumen de comisiones acumuladas (Bold / Addi / Transferencia) por mes |
| 4.3 | Filtro de rango libre de fechas en el panel Historial |
| 4.4 | Botón imprimir reporte directamente a impresora |

### Fase 5 — Funcionalidad Avanzada ✅
| # | Mejora |
|---|--------|
| 5.1 | Gráfica de tendencia últimos 7 días en Dashboard (QPainter, ganancia neta diaria) |
| 5.2 | Registro de auditoría (`log_acciones`: quién hizo qué y cuándo) + visor en Configuración |
| 5.3 | Campo de escaneo de código de barras en formulario de venta |
| 5.4 | Multi-usuario: tabla `usuarios`, `LoginDialog`, roles Admin/Vendedor, cerrar sesión |

### Fase 6 — UX y Apariencia ✅
| # | Mejora |
|---|--------|
| 6.1 | Modo oscuro: toggle en Configuración para cambiar tema claro/oscuro |
| 6.2 | Tiempo de timeout de sesión configurable desde el panel Configuración (1–60 min) |

### Fase 7 — Cierre de auditoría de mejoras pendientes ✅
| # | Mejora |
|---|--------|
| 7.1 | **Talla editable en inventario** — columna real `talla` en BD (antes se inferí­a del nombre del producto con regex `-T:M`); migración con backfill automático que limpia los nombres existentes; formularios de edición e ingreso, cargue de pedidos PDF, export Excel y PDF actualizados |
| 7.2 | **Filtro en el panel de auditoría** — combo "Todo / Solo configuración / Solo usuarios / Solo sesiones" sobre el log de `log_acciones` ya existente en Configuración |
| 7.3 | **Impresión directa de inventario** — botón "🖨 Imprimir" junto a "⬇ PDF"; genera el PDF a un archivo temporal y abre el diálogo de impresión de Windows (mismo patrón que el reporte mensual de Historial) |
| 7.4 | **Backup automático programado** — además del backup al arrancar, un timer periódico (configurable en horas, activable/desactivable) ejecuta backups mientras la app permanece abierta; configurable desde Configuración → Apariencia y Sesión |
| 7.5 | **Gráfica de tendencia de 7 días en el PDF mensual** — el PDF de reporte mensual ya tenía una gráfica de ingresos diarios; se agregó la gráfica de ganancia neta de los últimos 7 días (verde/rojo alrededor de línea de cero) que replica la del Dashboard |
| 7.6 | **Edición masiva de ventas** — botón "✏ Cambiar método (seleccionadas)" en Ventas del Día: selecciona varias ventas del mismo día (Ctrl/Shift+clic) y cambia el método de pago en lote, recalculando comisión y movimientos de cuentas para cada una; excluye automáticamente ventas con pago combinado |
| 7.7 | **Recordatorios activos periódicos** — el aviso de notas/facturas/fiados próximos a vencer (ya existente al iniciar la app) ahora se repite cada 4 horas mientras la app permanece abierta, no solo una vez al arrancar |
| 7.8 | **Modo resumen para el rol Vendedor en el Dashboard** — se ocultan costos, comisiones, ganancia bruta/neta, utilidad real, gastos del día, metas/utilidad de la proyección mensual, comisiones del mes y la gráfica de tendencia; el vendedor solo ve ventas, ingresos, ingresos por método y productos vendidos (sin la columna de ganancia) |
| 7.9 | **Calculadora — selector "% Margen real" vs "% Sobre costo"** — toggle en la cabecera de la Calculadora que cambia si las chips/spinbox de porcentaje representan el margen real sobre el precio de venta o el markup tradicional sobre el costo; afecta los módulos "Precio de Venta" y "Cascos desde Factura"; por defecto inicia en margen real |
| 7.10 | **Calculadora — comparación contra el método tradicional + explicación de fórmulas** — el resultado ahora muestra, con el mismo % elegido, cuánto daría el precio bajo la interpretación contraria (ej. "Con el método tradicional (30% sobre costo): $481.000" cuando se está en modo margen real); al final del panel se agregó un bloque con las fórmulas de ambos modos y una breve explicación de por qué el margen real es el indicador confiable (coincide con cómo se mide la rentabilidad en Dashboard/Historial), mientras que el margen sobre costo infla la percepción de ganancia |
| 7.11 | **Admin sin restricciones de contraseña tras inactividad** — el timeout de sesión volvía a bloquear Configuración/Exportar/Cuentas para todos los roles por igual tras N minutos de inactividad, obligando al admin a reingresar la contraseña aunque ya estuviera autenticado; ahora `_bloquear_sesion()` no afecta al rol admin |
| 7.12 | **Validación de nombre al crear usuarios** — el campo de nombre en Configuración → Usuarios limita a 50 caracteres (`setMaxLength`) y valida explícitamente al guardar, para evitar pegar texto largo por accidente (ver fix F7) |
| 7.13 | **Renombrado "Clientes Deudores" → "Apartados y Abonos de Clientes"** — el nombre original no dejaba claro si era dinero que debían o productos apartados; se renombró en el menú lateral, título del panel, checkboxes de Exportar/Importar y títulos del Excel exportado. Solo cambió el texto visible; el modelo, controlador, repositorio y tablas de BD (`Fiado`, `FiadoController`, `fiado`/`abonos_fiado`) conservan su nombre interno |
| 7.14 | **Campo "Abono inicial" al crear un apartado/deuda** — antes había que crear el registro y luego usar el botón "Abonar" por separado para reflejar lo que el cliente dejó al apartar/llevarse el producto; ahora el formulario "Nueva Deuda" tiene un campo opcional "Abono inicial ($)" que registra ese primer abono en el mismo paso de creación (solo visible al crear, no al editar) |
| 7.15 | **Importación más rápida y atómica** — `synchronous=NORMAL` en la conexión SQLite (recomendado por SQLite en modo WAL, acelera toda escritura de la app); la importación masiva de Excel ahora corre en una sola transacción (antes hacía ~1.500 commits individuales) — si algo falla a mitad de camino, se revierte todo en vez de dejar la BD a medias; se agregó un parámetro `commit` opcional a 14 funciones de escritura en `database/` (ventas, inventario, préstamos, facturas, abonos, gastos, notas, presupuesto, usuarios, configuración) sin cambiar su comportamiento por defecto en ningún otro lugar de la app |
| 7.16 | **Filtro de la nota instructiva al importar usuarios** — `_leer_usuarios()` ignoraba la fila de nota que el exportador escribe al final de la hoja "Usuarios", creando un usuario fantasma con ese texto como nombre en cada ciclo exportar→importar; ahora se descarta cualquier fila con nombre >50 caracteres o que empiece con "Roles válidos" |

### Fase 8 — Respaldo en Excel realmente completo (exportar/importar) ✅
Auditoría: se comparó cada una de las 18 tablas de datos de usuario contra lo que `services/exportador.py`/`services/importador.py` realmente exportan e importan de vuelta. Se encontraron 3 tipos de brecha y se cerraron todas:

| # | Mejora |
|---|--------|
| 8.1 | **Ventas — 8 campos que faltaban**: hora, vendedor, cliente (nombre/cédula/tel), N° factura, descuento, SKU, precio ofertado y grupo de venta no se exportaban ni importaban (solo 12 de 20 campos reales). Se añadió una hoja "Ventas" extendida (22 columnas) usada solo en el respaldo completo — las plantillas manuales de carga de ventas siguen con el formato simple de 12 columnas para no complicar el llenado a mano |
| 8.2 | **Inventario** — se agregó "Stock mínimo" a la exportación/importación; además se corrigió que el importador nunca leía la Talla de vuelta aunque sí se exportaba |
| 8.3 | **Facturas** — se agregó la columna "Cuenta" (de qué medio de pago salió) a la exportación/importación |
| 8.4 | **Configuración** — solo se exportaban 11 de 19 campos; se agregaron las 5 comisiones por cuenta (Nequi/NU/QR/Daviplata/Datafono) y los 2 ajustes de backup automático |
| 8.5 | **Cuentas, Movimientos de Cuentas, Cierres Mensuales, Fiado, Abonos de Fiado y Movimientos de Inventario** — antes se exportaban pero el importador no tenía ninguna función para leerlas de vuelta; si se restauraba desde un backup, esos datos se perdían aunque estuvieran en el archivo. Ahora las 6 hojas son completamente importables, vinculando cada registro a su cuenta/producto/factura por nombre (los ids cambian al reinsertar) |
| 8.6 | **Facturas Items y Log de Auditoría** — no se exportaban en absoluto; ahora ambas hojas se generan en el respaldo completo. El log de auditoría se **agrega** al existente al importar (nunca lo reemplaza, es un historial acumulable) |
| 8.7 | **Toda la importación corre en una sola transacción atómica** — si algo falla a mitad de camino, se revierte todo (ver 7.15); se probó forzando un fallo deliberado y confirmando reversión total, incluyendo las 6 tablas nuevas de este punto |

**Bugs reales corregidos en el camino** (no solo huecos, datos que se perdían o vinculaban mal):
- La columna "Cuenta" en "Mov. Cuentas" guardaba el ID numérico en vez del nombre — se rompía al reimportar si los IDs cambiaban tras recrear las cuentas.
- Importar Configuración **resetaba la contraseña** al valor de fábrica (nunca se preservaba la actual) — ahora se preserva siempre.
- Colisión de palabra clave en el detector de columnas de inventario: "Stock mínimo" se confundía con "Cantidad" (ambas contienen "stock") — se corrigió el orden de detección.

**Limitación conocida (no corregible sin riesgo):** los movimientos de inventario guardan el nombre del producto como texto, no un id estable — si un producto se renombra (ej. la limpieza de tallas de la Fase 1), sus movimientos históricos ya no se pueden vincular al reimportar un backup anterior al renombre. Es inherente al diseño, no un bug.

**Verificación de ciclo completo:** se exportó todo desde una copia de la BD real, se vaciaron las 14 tablas (incluyendo borrar un usuario a propósito), se reimportó, y las 13 tablas comparables quedaron idénticas — incluido el usuario recuperado y la contraseña intacta. Auditoría posterior de no-regresión: se probaron formatos de Excel anteriores a esta fase (compatibilidad hacia atrás), el flujo de "Importar Inventario" independiente, y los flujos normales de venta/factura/fiado/préstamo/inventario fuera de import-export — todo sin cambios de comportamiento.

### Fixes y mejoras post-fases ✅
| # | Descripción |
|---|-------------|
| F1 | **Combo negro en Método de Pago** — `_get_combo_style()` incluye colores explícitos y regla `QAbstractItemView` para evitar el fondo negro del sistema OS en Windows 11 (afectaba también a talla, sub-tipo de transferencia y pagos combinados) |
| F2 | **Soporte de logo e icono** — detección automática desde carpeta `assets/`; cualquier PNG/JPG se usa como logo del sidebar; `.ico`/`.png` como icono de ventana y taskbar; compatible con PyInstaller |
| F3 | **Exportación verificada** — confirmado que las 10 tablas de datos de usuario se exportan correctamente cuando todos los checkboxes están activos (ventas, préstamos, inventario, facturas, abonos, gastos, notas, configuración, usuarios, presupuesto) |
| F4 | **Auto-refresh al cambiar gastos operativos** — nueva señal `gastos_actualizados` en `VentasDiaPanel`; al agregar o eliminar un gasto se propaga automáticamente a Dashboard, Historial y Presupuesto sin necesidad de cerrar la app; botón `⟳ Actualizar` añadido al Dashboard |
| F5 | **Propagación completa de refreshes tras importación** — `_on_datos_importados()` ahora refresca también Préstamos, Notas y Presupuesto (antes quedaban desactualizados y había que hacer workarounds como toggle de filtros); botón `⟳ Actualizar` añadido al panel Préstamos |
| F6 | **Sección Cuentas** — control de saldo por medio de pago (Efectivo, Nequi, QR, NU, Daviplata, Addi); ventas nuevas acreditan automáticamente la cuenta correspondiente (incluyendo pagos combinados); ajuste manual de saldo; transferencias entre cuentas; historial de movimientos filtrable; cierres mensuales con snapshot histórico; solo Admin, protegida por contraseña — archivos: `models/cuenta.py`, `database/cuentas_repo.py`, `ui/cuentas_panel.py` |
| F7 | **Usuario fantasma con nombre corrupto** — se detectó (y eliminó de la BD de producción, dos veces) un usuario con rol "vendedor" cuyo nombre era texto largo pegado por accidente (probablemente la nota de la hoja "Usuarios" del Excel exportado, copiada al portapapeles y pegada en el campo Nombre al crear un usuario, y luego reintroducida al re-importar un backup viejo); aparecía en el combo de Vendedor de Registrar Venta y se exportaba como fila de usuario válida. Ver mejoras 7.12 y 7.16 para las validaciones que previenen que se repita. |
| F8 | **CRÍTICO — App "congelada" en la pantalla de inicio** — `main.py` llamaba `_splash.finish(window)` *antes* de mostrar la ventana principal (`window.showMaximized()`). Si la construcción de `MainWindow` tardaba más de 800ms (probable con datos reales: ventas, inventario, facturas), el aviso de recordatorios (`QTimer.singleShot(800, _alertar_facturas_vencimiento)`, ya programado al final de `MainWindow.__init__`) quedaba vencido y se disparaba justo durante `finish()`, abriendo un `QMessageBox` modal *mientras la ventana principal aún no era visible* — el diálogo quedaba escondido detrás del splash (que siempre está encima de todo), esperando un clic que nadie podía ver, y la app parecía congelada para siempre. Diagnosticado con `py-spy` (stack trace del proceso en vivo) tras descartar antivirus, hardware y permisos de usuario. Arreglado invirtiendo el orden: cerrar el splash y mostrar la ventana *antes* de que pueda disparar cualquier aviso pendiente. Verificado de forma determinística (sin clics manuales) confirmando que el diálogo ahora aparece después de que la ventana ya es visible. |
| F9 | **Columna "Desglose pagos" legible en el Excel de Ventas** — la columna técnica "Pagos JSON" (necesaria para que el importador reconstruya el pago exacto al restaurar un backup) mostraba el JSON crudo, ej. `[{"metodo": "Efectivo", "monto": 50000.0}, ...]`, difícil de leer para un humano abriendo el Excel. Se agregó una columna nueva al final de la hoja "Ventas" del respaldo completo, "Desglose pagos", con el mismo formato legible que ya usa la app en otras pantallas (ej. "Efectivo: $50,000 \| Transferencia NEQUI: $145,000"). Es solo de lectura — el importador sigue usando exclusivamente "Pagos JSON" para no perder precisión |

---

## Notas técnicas

- **Backup automático**: se ejecuta al arrancar, guarda hasta 7 copias rotativas en la carpeta `backups/`. Antes de una importación también se hace backup automático. Además, un timer programado (configurable en horas desde Configuración, activable/desactivable) repite el backup mientras la app permanece abierta.
- **Recordatorios activos**: al arrancar (y luego cada 4 horas mientras la app está abierta) se revisan notas próximas a vencer, facturas próximas y fiados con más de 30 días pendientes, mostrando un aviso si hay algo urgente.
- **Impresora térmica**: compatible con ESC/POS vía USB. Se configura por nombre de Windows en el panel Configuración. Si no hay impresora configurada, los recibos se generan como PDF.
- **Escaneo de barras**: el campo de escaneo en el formulario de venta acepta cualquier lector USB HID (se comporta como teclado). Al presionar Enter busca el código en inventario y lo agrega al carrito.
- **Pagos combinados**: una venta puede dividirse entre varios métodos de pago. La comisión se calcula proporcionalmente sobre cada parte.
- **Auditoría**: cada acción relevante (inicio/cierre de sesión, acceso a páginas protegidas, creación/eliminación de usuarios, exportación, importación, cambio de contraseña) queda registrada en `log_acciones` con usuario, fecha, hora y detalle.
