@echo off
echo ================================================================================
echo     YJBMOTOCOM - Instalacion de Dependencias
echo ================================================================================
echo.

echo Verificando Python...
python --version
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Python no esta instalado o no esta en el PATH.
    echo Por favor, instale Python desde https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo.
echo Instalando dependencias...
echo.

pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Hubo un problema instalando las dependencias.
    echo.
    pause
    exit /b 1
)

echo.
echo ================================================================================
echo     Instalacion completada exitosamente!
echo ================================================================================
echo.
echo Ahora puede ejecutar la aplicacion haciendo doble clic en EJECUTAR.bat
echo o ejecutando: python main.py
echo.
pause
