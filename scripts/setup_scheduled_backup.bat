@echo off
REM Setup Automated Daily Database Backups
REM Run this script as Administrator

echo =====================================
echo Mini Golf Database Backup Setup
echo =====================================
echo.

REM Check for admin rights
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] This script must be run as Administrator!
    echo.
    echo To run as Administrator:
    echo 1. Right-click on this batch file
    echo 2. Select "Run as Administrator"
    echo.
    pause
    exit /b 1
)

REM Get the script directory
set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..
set BATCH_FILE=%SCRIPT_DIR%run_backup.bat

echo [INFO] Creating scheduled task...
echo.

REM Delete existing task if it exists
schtasks /Query /TN "MiniGolfDatabaseBackup" >nul 2>&1
if %errorLevel% equ 0 (
    echo [INFO] Removing existing task...
    schtasks /Delete /TN "MiniGolfDatabaseBackup" /F >nul 2>&1
)

REM Create the scheduled task
schtasks /Create ^
    /TN "MiniGolfDatabaseBackup" ^
    /TR "\"%BATCH_FILE%\"" ^
    /SC DAILY ^
    /ST 02:00 ^
    /RL HIGHEST ^
    /F

if %errorLevel% equ 0 (
    echo.
    echo [OK] Scheduled task created successfully!
    echo.
    echo Task Details:
    echo   Name: MiniGolfDatabaseBackup
    echo   Schedule: Daily at 2:00 AM
    echo   Script: %BATCH_FILE%
    echo   Logs: %PROJECT_ROOT%\logs\backup.log
    echo.
    echo The backup will run automatically every day at 2:00 AM
    echo.
    echo To manage this task:
    echo   - Open Task Scheduler (taskschd.msc^)
    echo   - Find 'MiniGolfDatabaseBackup' in Task Scheduler Library
    echo.

    REM Ask if user wants to run test backup
    set /p TEST_BACKUP="Would you like to run a test backup now? (y/n): "
    if /i "%TEST_BACKUP%"=="y" (
        echo.
        echo [INFO] Running test backup...
        call "%BATCH_FILE%"
        echo.
        echo [OK] Test backup completed!
        echo Check %PROJECT_ROOT%\logs\backup.log for details
        echo.
    )
) else (
    echo.
    echo [ERROR] Failed to create scheduled task!
    echo.
)

pause
