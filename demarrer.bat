@echo off
rem Double-cliquer sur ce fichier pour installer (si besoin) puis lancer BioAccess.
chcp 65001 >nul
title BioAccess
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0demarrer.ps1" %*
echo.
pause
