@echo off
setlocal EnableExtensions
cd /d "%~dp0"
chcp 65001 >nul

call "%~dp0stop.bat"
