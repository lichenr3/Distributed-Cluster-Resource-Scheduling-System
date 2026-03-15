@echo off
chcp 65001 >nul 2>&1
title Mini Scheduler - Launcher

:: ============================================================
::  Mini Scheduler Startup Script
::  Starts: Master (8000) + Worker-1 (8001) + Worker-2 (8002) + Frontend (5173)
:: ============================================================

set "ROOT=%~dp0"
set "BACKEND=%ROOT%backend"
set "FRONTEND=%ROOT%frontend"

:: ---------- Preflight checks ----------

where uv >nul 2>&1
if errorlevel 1 (
    echo [ERROR] uv not found. Install: https://docs.astral.sh/uv/getting-started/installation/
    pause
    exit /b 1
)

where node >nul 2>&1
if errorlevel 1 (
    echo [ERROR] node not found. Install Node.js ^>=20.19.0
    pause
    exit /b 1
)

if not exist "%BACKEND%\.venv" (
    echo [INFO] Creating backend venv and installing dependencies...
    pushd "%BACKEND%"
    uv sync
    if errorlevel 1 (
        echo [ERROR] Backend dependency installation failed. Please run 'cd backend ^&^& uv sync' manually.
        popd
        pause
        exit /b 1
    )
    popd
    echo [INFO] Backend dependencies installed successfully.
)

if not exist "%FRONTEND%\node_modules" (
    echo [INFO] Installing frontend dependencies (this may take a few minutes on first run)...
    pushd "%FRONTEND%"
    call npm install
    if errorlevel 1 (
        echo [ERROR] Frontend dependency installation failed. Please run 'cd frontend ^&^& npm install' manually.
        popd
        pause
        exit /b 1
    )
    popd
    echo [INFO] Frontend dependencies installed successfully.
)

:: ---------- Start Master ----------
echo [START] Master on :8000
start "Master :8000" cmd /k "cd /d "%BACKEND%" && uv run python run_master.py"

:: Wait for Master to be ready before starting workers
echo [WAIT] Waiting for Master to be ready...
timeout /t 5 /nobreak >nul

:: ---------- Start Workers ----------
echo [START] Worker-1 on :8001 (cpu=4, mem=8)
start "Worker-1 :8001" cmd /k "cd /d "%BACKEND%" && uv run python run_worker.py --port 8001 --cpu 4 --mem 8"

echo [START] Worker-2 on :8002 (cpu=2, mem=4)
start "Worker-2 :8002" cmd /k "cd /d "%BACKEND%" && uv run python run_worker.py --port 8002 --cpu 2 --mem 4"

:: ---------- Start Frontend ----------
echo [START] Frontend on :5173
start "Frontend :5173" cmd /k "cd /d "%FRONTEND%" && npm run dev"

:: ---------- Done ----------
echo.
echo ============================================================
echo   All services started:
echo     Master   : http://localhost:8000
echo     Worker-1 : http://localhost:8001  (cpu=4, mem=8)
echo     Worker-2 : http://localhost:8002  (cpu=2, mem=4)
echo     Frontend : http://localhost:5173
echo ============================================================
echo.
echo Close this window or press any key to exit (services keep running).
pause >nul
