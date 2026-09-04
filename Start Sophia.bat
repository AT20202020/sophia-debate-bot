@echo off
setlocal EnableDelayedExpansion
title Sophia - Debate Bot Launcher

REM This launcher is self-installing: on a clean checkout it detects a
REM compatible Python, creates the sophia-env venv, installs
REM requirements.txt, checks Ollama is installed and has the model
REM pulled, and warns (without blocking) about the optional espeak-ng
REM and whisper-server pieces. Every check either fixes itself or prints
REM exactly what to do and where to get it - nothing should require
REM reading the README just to get a first run working.
set "SCRIPT=%~dp0debate_voice.py"
set "VENV_DIR=%~dp0sophia-env"
set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"
set "REQ_FILE=%~dp0requirements.txt"
set "REQ_HASH_FILE=%~dp0.requirements.sha256"
set "MODEL_NAME=qwen3.8:27b"

REM whisper.cpp GPU transcription server - optional, lives in the
REM whisper-server subfolder if you've set it up (gitignored - it's
REM large, machine-specific binaries, not code; see the README's
REM "Optional GPU transcription" section). debate_voice.py talks to it
REM over HTTP on 8090 and falls back automatically to slower CPU
REM transcription if it's not present or not reachable, so skipping
REM this setup entirely is fine.
set "WHISPER_EXE=%~dp0whisper-server\whisper-server.exe"
set "WHISPER_MODEL=%~dp0whisper-server\ggml-small.en.bin"

echo ============================================
echo   Sophia - Agnostic Atheist Debate Bot
echo ============================================
echo.

if not exist "%SCRIPT%" (
    echo [ERROR] debate_voice.py not found at:
    echo   %SCRIPT%
    echo This launcher must live in the same folder as debate_voice.py.
    pause
    exit /b 1
)

REM --- curl is used by every check below (Ollama, whisper-server) ---------
where curl >nul 2>&1
if errorlevel 1 (
    echo [ERROR] curl not found. It ships with Windows 10/11 by default -
    echo if it's missing, something unusual has been done to this machine.
    echo Install curl and re-run this launcher.
    pause
    exit /b 1
)

REM --- Find a compatible Python (3.10 - 3.12; kokoro cannot install on
REM 3.13+) and remember how to invoke it, preferring the newest ----------
echo Checking for a compatible Python (3.10-3.12)...
set "PYCMD="
for %%V in (3.12 3.11 3.10) do (
    if not defined PYCMD (
        py -%%V -V >nul 2>&1
        if not errorlevel 1 set "PYCMD=py -%%V"
    )
)
if not defined PYCMD (
    REM No py launcher, or none of those versions registered with it -
    REM fall back to whatever "python" resolves to and check its version
    REM via plain text matching. Deliberately avoids "python -c" here -
    REM parentheses inside a quoted -c argument, nested inside this
    REM if-block, are a known cmd.exe block-parsing trap.
    where python >nul 2>&1
    if not errorlevel 1 (
        for /f "usebackq delims=" %%L in (`python --version 2^>^&1`) do set "PYVER_LINE=%%L"
        echo !PYVER_LINE! | findstr /r /c:"Python 3\.1[0-2]\." >nul
        if not errorlevel 1 set "PYCMD=python"
    )
)
if not defined PYCMD (
    echo [ERROR] No compatible Python found ^(need 3.10, 3.11, or 3.12 -
    echo 3.12 is what this project is tested on; 3.13+ fails to install
    echo the "kokoro" package^).
    echo Install it from https://www.python.org/downloads/ and check
    echo "Add python.exe to PATH" during setup, then re-run this launcher.
    pause
    exit /b 1
)
echo Using: !PYCMD!

REM --- Create the venv if it doesn't exist yet -----------------------------
if not exist "%VENV_PYTHON%" (
    echo Creating virtual environment at sophia-env ...
    !PYCMD! -m venv "%VENV_DIR%"
    if not exist "%VENV_PYTHON%" (
        echo [ERROR] Failed to create the virtual environment at:
        echo   %VENV_DIR%
        pause
        exit /b 1
    )
)

REM --- Install/refresh dependencies, but only when requirements.txt has
REM actually changed since the last successful install (hashed via
REM certutil, built into Windows) - keeps every normal launch after the
REM first one fast instead of re-running pip every time. -----------------
set "NEWHASH="
for /f "skip=1 delims=" %%H in ('certutil -hashfile "%REQ_FILE%" SHA256 2^>nul') do if not defined NEWHASH set "NEWHASH=%%H"
set "NEWHASH=%NEWHASH: =%"
set "OLDHASH="
if exist "%REQ_HASH_FILE%" set /p OLDHASH=<"%REQ_HASH_FILE%"

if /i not "%NEWHASH%"=="%OLDHASH%" (
    echo Installing Python dependencies - first run only takes a few
    echo minutes ^(this pulls PyTorch as a Kokoro dependency^)...
    "%VENV_PYTHON%" -m pip install --upgrade pip --quiet
    "%VENV_PYTHON%" -m pip install -r "%REQ_FILE%"
    if errorlevel 1 (
        echo [ERROR] pip install failed - see the output above for details.
        pause
        exit /b 1
    )
    if defined NEWHASH echo %NEWHASH%> "%REQ_HASH_FILE%"
) else (
    echo Python dependencies already installed and up to date.
)

REM --- espeak-ng: needed by Kokoro to phonemize out-of-dictionary words.
REM Soft requirement - missing it degrades pronunciation of unusual
REM words rather than crashing, so this warns and continues rather than
REM exiting. -----------------------------------------------------------
set "ESPEAK_OK=0"
where espeak-ng >nul 2>&1 && set "ESPEAK_OK=1"
if "!ESPEAK_OK!"=="0" if exist "%ProgramFiles%\eSpeak NG\espeak-ng.exe" set "ESPEAK_OK=1"
if "!ESPEAK_OK!"=="0" (
    where winget >nul 2>&1
    if not errorlevel 1 (
        echo espeak-ng not found - attempting install via winget...
        winget install --id eSpeak-NG.eSpeak-NG -e --silent --accept-package-agreements --accept-source-agreements >nul 2>&1
        where espeak-ng >nul 2>&1 && set "ESPEAK_OK=1"
        if exist "%ProgramFiles%\eSpeak NG\espeak-ng.exe" set "ESPEAK_OK=1"
    )
)
if "!ESPEAK_OK!"=="0" (
    echo [WARNING] espeak-ng not found - Kokoro may mispronounce unusual
    echo or out-of-dictionary words. For best results, install it from
    echo https://github.com/espeak-ng/espeak-ng/releases ^(the .msi^).
) else (
    echo espeak-ng found.
)

REM --- Ollama must be installed - there is no CPU/GPU fallback for the
REM LLM itself, so this is fatal if it can't be resolved. -----------------
where ollama >nul 2>&1
if errorlevel 1 (
    where winget >nul 2>&1
    if not errorlevel 1 (
        echo Ollama not found - attempting install via winget...
        winget install --id Ollama.Ollama -e --silent --accept-package-agreements --accept-source-agreements
        echo.
        echo Ollama was just installed. Windows needs a moment to update
        echo this terminal's PATH, so please close this window and run
        echo Start Sophia.bat again.
        pause
        exit /b 0
    )
)
where ollama >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Ollama is not installed and could not be installed
    echo automatically ^(winget unavailable^).
    echo Install it from https://ollama.com/download, then re-run this
    echo launcher.
    pause
    exit /b 1
)

REM --- GPU inference tuning (Jeff's speed investigation, Sept 2026) --------
REM Flash attention + a quantized KV cache speed up generation without
REM touching the model itself - same weights, same output, just cheaper
REM math per token. On AMD RDNA3 cards (7900 XTX = gfx1100), flash
REM attention needs THREE variables together, not just the first one:
REM HSA_OVERRIDE_GFX_VERSION tells ROCm which attention kernel to use -
REM without it, ROCm silently falls back to normal (unaccelerated)
REM attention while OLLAMA_FLASH_ATTENTION=1 still looks "on". These only
REM take effect when THIS launcher is the one starting ollama serve - if
REM Ollama is already running from a previous launch, fully quit it first
REM (or reboot) so it picks these up on its next start.
REM Harmless no-ops on NVIDIA/other AMD architectures - HSA_OVERRIDE_GFX_VERSION
REM and AMD_SERIALIZE_KERNEL are ROCm/RDNA3-specific and ignored otherwise.
set "OLLAMA_FLASH_ATTENTION=1"
set "HSA_OVERRIDE_GFX_VERSION=11.0.0"
set "AMD_SERIALIZE_KERNEL=3"
set "OLLAMA_KV_CACHE_TYPE=q8_0"

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

REM --- Make sure the model is pulled ---------------------------------------
set "OLLAMA_UP=0"
if "!OLLAMA_STATUS!"=="200" set "OLLAMA_UP=1"
if "!OLLAMA_UP!"=="0" (
    echo Skipping model check - Ollama isn't responding yet.
) else (
    ollama list | findstr /i /c:"%MODEL_NAME%" >nul
    if errorlevel 1 (
        echo Model %MODEL_NAME% not found - pulling it now. This is a large
        echo download ^(tens of GB^) and may take a while depending on your
        echo connection...
        ollama pull %MODEL_NAME%
        if errorlevel 1 (
            echo [ERROR] Failed to pull %MODEL_NAME%. Check your internet
            echo connection, then re-run this launcher.
            pause
            exit /b 1
        )
    ) else (
        echo Model %MODEL_NAME% already pulled.
    )
)

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
