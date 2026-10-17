@echo off
setlocal EnableDelayedExpansion
title Sophia model comparison
REM Same Sophia, same questions, two models: the one she runs now (A) and the
REM other one (B) - stock qwen3.8:27b now that she runs the abliterated model.
REM One fixed judge (model A) grades both. B must be installed (ollama pull qwen3.8:27b).
REM Nothing live is changed. Takes about 20-25 minutes.
REM Close Sophia AND let any training session finish first - they share the GPU.
REM The .bat makes sure qwen3.8-abliterated:27b exists first (make_abliterated_model.py).

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
echo Making qwen3.8-abliterated:27b (stock template + abliterated weights)...
"%PY%" -u make_abliterated_model.py
if errorlevel 1 (
    echo Could not make the model - see the message above.
    pause
    exit /b 1
)

echo.
"%PY%" -u sophia_compare.py

echo.
for /f "delims=" %%F in ('dir /b /ad /od "compare_runs" 2^>NUL') do set "LATEST=%%F"
if defined LATEST if exist "compare_runs\!LATEST!\COMPARE.md" (
    echo Opening compare_runs\!LATEST!\COMPARE.md - tell Claude the comparison finished.
    start "" notepad "compare_runs\!LATEST!\COMPARE.md"
)
pause
