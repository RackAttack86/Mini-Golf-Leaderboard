@echo off
REM Mini Golf Database Backup Script
REM This script is run by Windows Task Scheduler

cd /d "%~dp0.."
python scripts\backup_database.py >> logs\backup.log 2>&1
