@echo off
chcp 65001 >nul 2>&1
title Mini Scheduler - Stop All

:: ============================================================
::  Mini Scheduler Stop Script
::  Kills all running uvicorn and vite dev server processes
:: ============================================================

echo [STOP] Killing backend processes (uvicorn)...
taskkill /f /fi "WINDOWTITLE eq Master*"  >nul 2>&1
taskkill /f /fi "WINDOWTITLE eq Worker*"  >nul 2>&1

echo [STOP] Killing frontend process (vite)...
taskkill /f /fi "WINDOWTITLE eq Frontend*" >nul 2>&1

:: Fallback: kill by port if window titles were renamed
for %%P in (8000 8001 8002 5173) do (
    for /f "tokens=5" %%p in ('netstat -aon ^| findstr ":%%P " ^| findstr "LISTENING"') do (
        taskkill /f /pid %%p >nul 2>&1
    )
)

echo.
echo All services stopped.
pause
