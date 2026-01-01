@echo off
schtasks /Create /TN "MiniGolfDatabaseBackup" /TR "D:\Mini-Golf-Leaderboard\scripts\run_backup.bat" /SC DAILY /ST 00:00 /RL HIGHEST /F
