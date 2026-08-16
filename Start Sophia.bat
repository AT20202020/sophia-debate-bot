@echo off
setlocal EnableDelayedExpansion
title Sophia - Debate Bot Launcher

REM Both paths resolve relative to this .bat's own folder. Edit
REM VENV_PYTHON if your Python environment lives elsewhere (see README
REM setup - a venv named sophia-env next to this file is the default).
set "VENV_PYTHON=%~dp0sophia-env\Scripts\python.exe"
set "SCRIPT=%~dp0debate_voice.py"

echo ============================================
echo   Sophia - Agnostic Atheist Debate Bot
echo ============================================
echo.

REM --- Sanity checks -------------------------------------------------------
if not exist "%VENV_PYTHON%" (
    echo [ERROR] Python venv not found at:
    echo   %VENV_PYTHON%
    echo Check that open-webui-env exists in your user folder.
    pause
    exit /b 1
)

if not exist "%SCRIPT%" (
    echo [ERROR] debate_voice.py not found at:
    echo   %SCRIPT%
    pause
    exit /b 1
)

REM --- Make sure Ollama is running -----------------------------------------
echo Checking if Ollama is running...
curl -s -o NUL -w "%%{http_code}" http://localhost:11434/api/tags > "%TEMP%\sophia_ollama_check.txt" 2>NUL
set /p OLLAMA_STATUS=<"%TEMP%\sophia_ollama_check.txt"

if "!OLLAMA_STATUS!"=="200" (
    echo Ollama is already running.
) else (
    echo Ollama not responding - starting it...
    start "" ollama serve
    echo Waiting for Ollama to come online...

    set OLLAMA_READY=0
    for /L %%i in (1,1,15) do (
        if "!OLLAMA_READY!"=="0" (
            curl -s -o NUL -w "%%{http_code}" http://localhost:11434/api/tags > "%TEMP%\sophia_ollama_check.txt" 2>NUL
            set /p OLLAMA_STATUS=<"%TEMP%\sophia_ollama_check.txt"
            if "!OLLAMA_STATUS!"=="200" (
                set OLLAMA_READY=1
                echo Ollama is up.
            ) else (
                timeout /t 2 /nobreak >NUL
            )
        )
    )

    if "!OLLAMA_READY!"=="0" (
        echo [WARNING] Ollama did not respond after ~30s.
        echo Sophia will still launch, but may fail to reach the model until Ollama starts.
    )
)

del "%TEMP%\sophia_ollama_check.txt" >NUL 2>&1

REM --- Launch Sophia ---------------------------------------------------------
echo.
echo Launching Sophia...
echo.
"%VENV_PYTHON%" "%SCRIPT%"

echo.
echo Sophia has exited.
pause
