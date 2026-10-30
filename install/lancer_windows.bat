@echo off
rem Lance VISU PTBG avec l'environnement créé par installer_windows.bat.
rem Usage : install\lancer_windows.bat [fichier1.csv fichier2.csv ...]
setlocal
set PROJET=%~dp0..
"%PROJET%\.venv\Scripts\python.exe" "%PROJET%\MAIN.py" %*
endlocal
