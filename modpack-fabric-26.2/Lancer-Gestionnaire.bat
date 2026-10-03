@echo off
chcp 65001 >nul
title Gestionnaire - Optimisation Fabric 26.2
cd /d "%~dp0"
where py >nul 2>&1 && (py -3 gestionnaire.py %* & goto fin)
where python >nul 2>&1 && (python gestionnaire.py %* & goto fin)
echo.
echo Python 3 n'est pas installe.
echo Telecharge-le sur https://www.python.org/downloads/ et coche "Add python.exe to PATH" pendant l'installation.
echo.
pause
:fin
if errorlevel 1 pause
