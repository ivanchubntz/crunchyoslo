@echo off
cd /d "%~dp0"
where pythonw.exe >nul 2>nul
if %errorlevel% equ 0 (
    start "" pythonw.exe "%~dp0app.pyw"
    exit /b 0
)
where pyw.exe >nul 2>nul
if %errorlevel% equ 0 (
    start "" pyw.exe "%~dp0app.pyw"
    exit /b 0
)
echo No se encontro Python para ejecutar Oslo.
echo Instala Python 3 para Windows con Tcl/Tk y vuelve a abrir este archivo.
pause
