# YJBMOTOCOM — Plan de Mejoras por Fases

Documento de seguimiento del roadmap de mejoras acordado con el usuario.
Actualizar el estado de cada ítem conforme se completen.

---

## FASE 1 — Seguridad ✅ EN CURSO

| # | Mejora | Estado |
|---|--------|--------|
| 1.1 | Hash de contraseña con SHA-256 (ya no se guarda en texto plano) | ✅ Completado |
| 1.2 | Migración automática de contraseña plain-text → hash al arrancar | ✅ Completado |
| 1.3 | Timeout de sesión: bloqueo automático tras N minutos de inactividad | ✅ Completado |
| 1.4 | Protección de hojas Excel al exportar (worksheets read-only con contraseña) | ✅ Completado |
| 1.5 | Panel Exportar/Importar protegido por contraseña (ya implementado sesión anterior) | ✅ Completado |

---

## FASE 2 — Estabilidad y Mantenimiento ✅ Completada

| # | Mejora | Estado |
|---|--------|--------|
| 2.1 | Log de errores a archivo `errors.log` (en vez de solo QMessageBox) | ✅ Completado |
| 2.2 | Migraciones de BD versionadas (tabla `schema_version`, versión actual = 7) | ✅ Completado |
| 2.3 | 30 tests automáticos: security, calculator, migraciones | ✅ Completado |

---

## FASE 3 — Alertas y Búsqueda ✅ Completada

| # | Mejora | Estado |
|---|--------|--------|
| 3.1 | Alerta al arrancar + badge en sidebar si hay facturas venciendo ≤ 7 días | ✅ Completado |
| 3.2 | Búsqueda global en sidebar: inventario, facturas, ventas con debounce 250ms | ✅ Completado |
| 3.3 | Notas con fecha límite (migración 8), badge vencidas en sidebar, diálogo mejorado | ✅ Completado |

---

## FASE 4 — Reportes y Exportación ✅ Completada

| # | Mejora | Estado |
|---|--------|--------|
| 4.1 | Exportar reporte mensual a PDF (ya existe reportlab instalado) | ✅ Completado |
| 4.2 | Resumen de comisiones acumuladas (Bold / Addi / Transferencia) por mes/año | ✅ Completado |
| 4.3 | Filtro de rango libre de fechas en el panel Historial | ✅ Completado |
| 4.4 | Botón imprimir reporte directamente a impresora | ✅ Completado |

---

## FASE 5 — Funcionalidad Avanzada ✅ Completada

| # | Mejora | Estado |
|---|--------|--------|
| 5.1 | Gráfica de tendencia últimos 7 días en Dashboard (QPainter, ganancia neta diaria) | ✅ Completado |
| 5.2 | Registro de auditoría (`log_acciones`: quién, qué, cuándo) + visor en Configuración | ✅ Completado |
| 5.3 | Campo de escaneo de código de barras en formulario de venta (Enter → agrega al carrito) | ✅ Completado |
| 5.4 | Multi-usuario: tabla `usuarios`, `LoginDialog`, roles Admin/Vendedor, botón cerrar sesión | ✅ Completado |

---

## FASE 6 — UX y Apariencia ✅ Completada

| # | Mejora | Estado |
|---|--------|--------|
| 6.1 | Modo oscuro: toggle en Configuración para cambiar tema claro/oscuro | ✅ Completado |
| 6.2 | Configuración del tiempo de timeout de sesión desde el panel Configuración | ✅ Completado |

---

## Notas Técnicas

- **Contraseña**: almacenada como SHA-256 hex (64 chars) desde Fase 1. Detección automática de legacy plain-text en `utils/security.py`.
- **Timeout**: implementado con `QTimer` en `MainWindow`. Por defecto 10 minutos. Reinicio en cualquier evento de mouse/teclado.
- **Excel protegido**: hojas Inventario y Configuración con `sheet_state='locked'` + contraseña de worksheet en openpyxl.
- **Dependencias nuevas Fase 1**: ninguna (solo `hashlib` de la stdlib).
