@echo off
setlocal EnableDelayedExpansion
title Sophia - Debate Bot Launcher

REM Both paths resolve relative to this .bat's own folder. Edit
REM VENV_PYTHON if your Python environment lives elsewhere (see README
REM setup - a venv named sophia-env next to this file is the default).
set "VENV_PYTHON=%~dp0sophia-env\Scripts\python.exe"
set "SCRIPT=%~dp0debate_voice.py"

REM whisper.cpp GPU transcription server - optional, lives in the
REM whisper-server subfolder if you've set it up (gitignored - it's
REM large, machine-specific binaries, not code; see whisper-server\
REM README.txt or the README's "Optional GPU transcription" section).
REM debate_voice.py talks to it over HTTP on 8090 and falls back
REM automatically to slower CPU transcription if it's not present or
REM not reachable, so skipping this setup entirely is fine.
set "WHISPER_EXE=%~dp0whisper-server\whisper-server.exe"
set "WHISPER_MODEL=%~dp0whisper-server\ggml-small.en.bin"

echo ============================================
echo   Sophia - Agnostic Atheist Debate Bot
echo ============================================
echo.

REM --- Sanity checks -------------------------------------------------------
if not exist "%VENV_PYTHON%" (
    echo [ERROR] Python venv not found at:
    echo   %VENV_PYTHON%
    echo Check that sophia-env exists next to this file - see README setup.
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

REM --- Make sure the whisper.cpp GPU transcription server is running -------
REM Any real HTTP response (even 404/405 for a GET on this POST-only route)
REM proves the port is alive; "000" or blank means curl couldn't connect at
REM all, i.e. nothing is listening yet. Missing exe/model is NOT an error -
REM most people won't have this set up, and CPU fallback handles it.
echo Checking if the whisper.cpp GPU transcription server is running...
curl -s -o NUL -w "%%{http_code}" http://127.0.0.1:8090/inference > "%TEMP%\sophia_whisper_check.txt" 2>NUL
set /p WHISPER_STATUS=<"%TEMP%\sophia_whisper_check.txt"
del "%TEMP%\sophia_whisper_check.txt" >NUL 2>&1
if "!WHISPER_STATUS!"=="" set "WHISPER_STATUS=000"

if "!WHISPER_STATUS!"=="000" (
    if exist "%WHISPER_EXE%" (
        if exist "%WHISPER_MODEL%" (
            echo Whisper GPU server not running - starting it...
            start "Whisper Server" "%WHISPER_EXE%" -m "%WHISPER_MODEL%" --host 127.0.0.1 --port 8090
            echo Waiting for it to come online...
            set WHISPER_READY=0
            for /L %%i in (1,1,10) do (
                if "!WHISPER_READY!"=="0" (
                    curl -s -o NUL -w "%%{http_code}" http://127.0.0.1:8090/inference > "%TEMP%\sophia_whisper_check2.txt" 2>NUL
                    set /p WHISPER_STATUS2=<"%TEMP%\sophia_whisper_check2.txt"
                    if not "!WHISPER_STATUS2!"=="" if not "!WHISPER_STATUS2!"=="000" (
                        set WHISPER_READY=1
                        echo Whisper GPU server is up.
                    ) else (
                        timeout /t 2 /nobreak >NUL
                    )
                )
            )
            del "%TEMP%\sophia_whisper_check2.txt" >NUL 2>&1
            if "!WHISPER_READY!"=="0" (
                echo [WARNING] Whisper server did not respond after ~20s.
                echo Sophia will still launch and fall back to CPU transcription.
            )
        ) else (
            echo Whisper server not set up - continuing with CPU transcription.
        )
    ) else (
        echo Whisper server not set up - continuing with CPU transcription.
    )
) else (
    echo Whisper GPU server is already running.
)

REM --- Launch Sophia ---------------------------------------------------------
echo.
echo Launching Sophia...
echo.
"%VENV_PYTHON%" "%SCRIPT%"

echo.
echo Sophia has exited.
pause
