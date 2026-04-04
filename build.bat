@echo off
REM build.bat — Genera dist\YJBMOTOCOM\YJBMOTOCOM.exe con PyInstaller
REM Ejecutar desde la raíz del proyecto: build.bat
REM
REM Resultado: carpeta dist\YJBMOTOCOM\
REM   - Ejecutar con: dist\YJBMOTOCOM\YJBMOTOCOM.exe
REM   - Crear acceso directo al .exe en el escritorio

echo ============================================================
echo  YJBMOTOCOM — Build ejecutable
echo ============================================================

REM Limpiar builds anteriores
if exist build rmdir /s /q build
if exist dist  rmdir /s /q dist
if exist YJBMOTOCOM.spec del YJBMOTOCOM.spec

python -m PyInstaller ^
    --onedir ^
    --windowed ^
    --name "YJBMOTOCOM" ^
    --hidden-import "PySide6.QtXml" ^
    --hidden-import "PySide6.QtPrintSupport" ^
    --hidden-import "openpyxl" ^
    --hidden-import "openpyxl.cell._writer" ^
    main.py

echo.
if exist dist\YJBMOTOCOM\YJBMOTOCOM.exe (
    echo  [OK]  Ejecutable generado: dist\YJBMOTOCOM\YJBMOTOCOM.exe
    echo.
    echo  Para usar: copia la carpeta dist\YJBMOTOCOM\ a donde quieras
    echo  y crea un acceso directo a YJBMOTOCOM.exe
) else (
    echo  [ERROR]  No se genero el ejecutable. Revisa los mensajes arriba.
)
echo.
pause
