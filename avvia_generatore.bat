@echo off
cd /d "%~dp0"
py generator.py
if errorlevel 1 python generator.py
if errorlevel 1 pause
