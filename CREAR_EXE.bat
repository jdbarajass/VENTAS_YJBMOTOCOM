@echo off
echo ================================================================================
echo     YJBMOTOCOM - Crear Archivo Ejecutable (.EXE)
echo ================================================================================
echo.

cd /d "%~dp0"

echo Instalando PyInstaller...
pip install pyinstaller

echo.
echo Creando ejecutable...
echo Esto puede tardar varios minutos...
echo.

pyinstaller --onefile --windowed --name "YJBMOTOCOM" main.py

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Hubo un problema creando el ejecutable.
    echo.
    pause
    exit /b 1
)

echo.
echo ================================================================================
echo     Ejecutable creado exitosamente!
echo ================================================================================
echo.
echo El archivo se encuentra en: dist\YJBMOTOCOM.exe
echo.
echo IMPORTANTE:
echo - Copie la carpeta "data" al mismo directorio que el .exe
echo - El ejecutable puede tardar unos segundos en iniciar la primera vez
echo.

:: Abrir carpeta dist
explorer dist

pause
