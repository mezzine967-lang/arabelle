@echo off
rem Installation de VISU PTBG sur Windows 11 64 bits HORS Spyder (REQ_COMMON_KH_3000).
rem Sous Spyder 6, aucune installation n'est nécessaire : ouvrir MAIN.py et appuyer sur F5.
rem
rem Prérequis : Python 3.11 64 bits de python.org, option « tcl/tk and IDLE » cochée.
rem Crée l'environnement virtuel .venv à la racine du projet et y installe requirements.txt.
setlocal
set PROJET=%~dp0..
py -3.11 -c "import tkinter" || (echo Python 3.11 64 bits avec Tcl/Tk introuvable. & exit /b 1)
py -3.11 -m venv "%PROJET%\.venv" || exit /b 1
"%PROJET%\.venv\Scripts\python.exe" -m pip install -r "%PROJET%\requirements.txt" || exit /b 1
"%PROJET%\.venv\Scripts\python.exe" "%PROJET%\tools\audit_environnement.py"
echo Installation terminee. Lancement : install\lancer_windows.bat
endlocal
