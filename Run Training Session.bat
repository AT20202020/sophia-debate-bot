@echo off
setlocal EnableDelayedExpansion
title Sophia training session
REM One-hour training session (sophia_trainer.py):
REM   question bank -> Sophia answers (timed) -> code checks + judge ->
REM   Claude Code proposes one small fix -> kept only if accuracy goes up
REM   without slowing her down -> repeat until the hour is used.
REM Your live Sophia files are NOT changed. Results go to training_runs\<time>\.
REM Close Sophia first - both talking to Ollama at once skews the timings.
REM Change MINUTES below for a longer or shorter session.

set "MINUTES=60"

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

where claude >NUL 2>NUL
if errorlevel 1 (
    echo [NOTE] The claude command was not found, so this session will only MEASURE,
    echo        with no automatic tweaks. Install or log in to Claude Code to enable tweaks.
    echo.
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
"%PY%" -u sophia_trainer.py --minutes %MINUTES%

echo.
for /f "delims=" %%F in ('dir /b /ad /od "training_runs" 2^>NUL') do set "LATEST=%%F"
if defined LATEST (
    echo Opening training_runs\!LATEST!\REPORT.md - tell Claude the session finished.
    start "" notepad "training_runs\!LATEST!\REPORT.md"
)
pause
