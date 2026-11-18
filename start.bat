@echo off
setlocal EnableExtensions
cd /d "%~dp0"
chcp 65001 >nul

if /I "%~1"=="lan" (
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start.ps1" -Mode lan
) else (
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start.ps1" -Mode local
)

if errorlevel 1 pause
ping 127.0.0.1 -n 4 >nul
