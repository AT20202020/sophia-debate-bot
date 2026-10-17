@echo off
setlocal EnableDelayedExpansion
title Sophia debate simulator
REM Runs sophia_sim.py: simulated historicity debates (opponent argues FOR a
REM historical Jesus), each reviewed against the cards in knowledge\historicity.
REM Default: 20 debates x 6 exchanges, roughly 20 minutes.
REM Close Sophia first - both talking to Ollama at once skews everything.
REM
REM Extra options can be passed through, e.g.:
REM   "Run Simulator.bat" --debates 300          (overnight)
REM   "Run Simulator.bat" --styles scholar       (one opponent style only)
REM   "Run Simulator.bat" --resume sim_runs\20261015-190000
REM Ctrl+C stops cleanly and still writes the report.

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
"%PY%" -u sophia_sim.py %*
set "RC=!errorlevel!"

echo.
if "!RC!"=="0" (
    for /f "delims=" %%F in ('dir /b /ad /od "sim_runs" 2^>NUL') do set "LATEST=%%F"
    if defined LATEST (
        echo Opening sim_runs\!LATEST!\report.md - tell Claude when it's done.
        start "" notepad "sim_runs\!LATEST!\report.md"
    )
) else (
    echo The simulator stopped with an error ^(exit !RC!^). Copy the text above and paste it to Claude.
)
pause
