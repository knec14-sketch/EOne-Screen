@echo off
title EOne screen

rem Edinaya programma: ekran, temy, nastroyki.
rem Prava administratora nuzhny tolko dlya temperatury processora.

net session >nul 2>&1
if %errorlevel% neq 0 (
    powershell -NoProfile -Command "Start-Process -FilePath \"%~f0\" -Verb RunAs"
    exit /b
)
cd /d "%~dp0"
set PYW=
where pythonw >nul 2>&1 && set PYW=pythonw
if not defined PYW set PYW=python
start "" %PYW% app.py %*
exit /b
