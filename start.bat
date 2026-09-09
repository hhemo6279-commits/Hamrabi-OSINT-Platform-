@echo off
rem ============================================================
rem  Hamrabi One-Click Launcher (double-click this file)
rem  Starts the backend + frontend and opens the browser.
rem ============================================================
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"
pause