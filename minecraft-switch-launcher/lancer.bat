@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul && (py -3 launcher.py %* & goto fin)
where python >nul 2>nul && (python launcher.py %* & goto fin)
echo Python 3 est introuvable. Installez-le depuis https://www.python.org/downloads/
echo (cochez "Add python.exe to PATH" pendant l'installation).
:fin
pause
