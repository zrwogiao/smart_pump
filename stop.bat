@echo off
setlocal EnableExtensions
cd /d "%~dp0"
chcp 65001 >nul

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\stop.ps1"
if errorlevel 1 pause
ping 127.0.0.1 -n 3 >nul
