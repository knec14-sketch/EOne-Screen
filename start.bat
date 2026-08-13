@echo off
chcp 65001 >nul
title EOne screen - osmotr mashiny

rem Osmotr mashiny pered pervym zapuskom.
rem Chast proekta EOne screen. Avtor: EOne. Litsenziya: CC BY-NC-SA 4.0.
rem
rem Delaet tri veshchi, kotorye start.py sam za sebya sdelat ne mozhet:
rem   1. podnimaet prava administratora - bez nih temperatura processora
rem      ne chitaetsya v printsipe;
rem   2. snimaet so vseh faylov pometku "skachano iz interneta", iz-za
rem      kotoroy .NET otkazyvaetsya gruzit biblioteku datchikov;
rem   3. nahodit python i derzhit okno otkrytym, chtoby otchet mozhno
rem      bylo prochitat.
rem
rem VNIMANIE: v komandnoy stroke pisat imenno start.bat, a ne start -
rem slovo start u samoy cmd zanyato pod svoyu komandu.

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo   Nuzhny prava administratora. Sejchas Windows sprosit razreshenie.
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

cd /d "%~dp0"

echo.
echo   Snimayu pometku "skachano iz interneta"...
powershell -NoProfile -Command "Get-ChildItem -Path '%~dp0' -Recurse -File -ErrorAction SilentlyContinue | Unblock-File -ErrorAction SilentlyContinue"

set PY=
where python >nul 2>&1 && set PY=python
if not defined PY where py >nul 2>&1 && set PY=py
if not defined PY (
    echo.
    echo   Python ne nayden. Postav ego s python.org i otmet galochku
    echo   "Add python.exe to PATH" pri ustanovke.
    echo.
    pause
    exit /b 1
)

%PY% start.py %*

echo.
pause
