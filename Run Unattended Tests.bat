@echo off
setlocal EnableDelayedExpansion
title Sophia unattended tests
REM Runs two simulator batches back to back, no input needed:
REM   1. historicity debates (opponent argues Jesus existed)
REM   2. morality debates   (opponent runs the moral argument)
REM Each debate takes about 1 minute, so the default 60 + 60 is roughly 2 hours.
REM Change DEBATES below for a longer or shorter run (300 = about 10 hours).
REM Close Sophia first - both talking to Ollama at once skews everything.
REM Ctrl+C stops the current batch cleanly; its report is still written.

set "DEBATES=60"

cd /d "%~dp0"
REM Uses the sophia-env that Start Sophia.bat creates next to this file; falls
REM back to an older shared venv if that is what this machine has.
set "PY=%~dp0sophia-env\Scripts\python.exe"
if not exist "%PY%" set "PY=%USERPROFILE%\open-webui-env\Scripts\python.exe"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

if not exist "%PY%" (
    echo [ERROR] No Python environment found. Run Start Sophia.bat once first - it sets one up.
    pause
    exit /b 1
)

echo Checking Ollama...
set "OLLAMA_STATUS="
curl -s -o NUL -w "%%{http_code}" http://127.0.0.1:11434/api/tags > "%TEMP%\sophia_ollama_check.txt" 2>NUL
set /p OLLAMA_STATUS=<"%TEMP%\sophia_ollama_check.txt"
if not "!OLLAMA_STATUS!"=="200" (
    echo Ollama not responding - starting it...
    set "OLLAMA_FLASH_ATTENTION=1"
    set "OLLAMA_KV_CACHE_TYPE=q8_0"
    start "" /min ollama serve
    for /L %%i in (1,1,30) do (
        if not "!OLLAMA_STATUS!"=="200" (
            timeout /t 2 /nobreak >NUL
            curl -s -o NUL -w "%%{http_code}" http://127.0.0.1:11434/api/tags > "%TEMP%\sophia_ollama_check.txt" 2>NUL
            set /p OLLAMA_STATUS=<"%TEMP%\sophia_ollama_check.txt"
        )
    )
)
if not "!OLLAMA_STATUS!"=="200" (
    echo Ollama never came up after ~60s. Start it yourself and run this again.
    pause
    exit /b 1
)

echo.
echo ===== 1 of 2: historicity, %DEBATES% debates =====
"%PY%" -u sophia_sim.py --topic historicity --debates %DEBATES%

echo.
echo ===== 2 of 2: morality, %DEBATES% debates =====
"%PY%" -u sophia_sim.py --topic morality --debates %DEBATES%

echo.
echo All done. Tell Claude the tests finished - it will read both reports.
for /f "delims=" %%F in ('dir /b /ad /od "sim_runs\*-historicity" 2^>NUL') do set "LAST_H=%%F"
for /f "delims=" %%F in ('dir /b /ad /od "sim_runs\*-morality" 2^>NUL') do set "LAST_M=%%F"
if defined LAST_H start "" notepad "sim_runs\!LAST_H!\report.md"
if defined LAST_M start "" notepad "sim_runs\!LAST_M!\report.md"
pause
