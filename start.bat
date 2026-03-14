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
    echo [INFO] Creating backend venv...
    pushd "%BACKEND%"
    uv sync
    popd
)

if not exist "%FRONTEND%\node_modules" (
    echo [INFO] Installing frontend dependencies...
    pushd "%FRONTEND%"
    npm install
    popd
)

:: ---------- Start Master ----------
echo [START] Master on :8000
start "Master :8000" cmd /k "cd /d "%BACKEND%" && uv run python run_master.py"

:: Wait for Master to be ready before starting workers
echo [WAIT] Waiting for Master to be ready...
timeout /t 2 /nobreak >nul

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
