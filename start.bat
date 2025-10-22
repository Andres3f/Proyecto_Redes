@echo off
REM Ejecutar el script de configuración de red
python scripts/configure_network.py

REM Si el script de configuración se ejecutó correctamente, iniciar docker compose
if %ERRORLEVEL% EQU 0 (
    docker compose up --build
)