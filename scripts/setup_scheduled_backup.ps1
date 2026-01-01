# Setup Automated Daily Database Backups
# Run this script as Administrator to create the scheduled task

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "Mini Golf Database Backup Setup" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Get the script directory
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptPath
$batchFile = Join-Path $scriptPath "run_backup.bat"

# Task details
$taskName = "MiniGolfDatabaseBackup"
$taskDescription = "Daily backup of Mini Golf Leaderboard database"
$taskTime = "12:00AM"  # Midnight daily

# Check if running as administrator
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
$isAdmin = $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "[ERROR] This script must be run as Administrator!" -ForegroundColor Red
    Write-Host ""
    Write-Host "To run as Administrator:" -ForegroundColor Yellow
    Write-Host "1. Right-click on PowerShell" -ForegroundColor Yellow
    Write-Host "2. Select 'Run as Administrator'" -ForegroundColor Yellow
    Write-Host "3. Navigate to: $scriptPath" -ForegroundColor Yellow
    Write-Host "4. Run: .\setup_scheduled_backup.ps1" -ForegroundColor Yellow
    Write-Host ""
    pause
    exit 1
}

# Check if task already exists
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue

if ($existingTask) {
    Write-Host "[INFO] Scheduled task already exists." -ForegroundColor Yellow
    Write-Host ""
    $response = Read-Host "Do you want to recreate it? (yes/no)"

    if ($response -ne "yes") {
        Write-Host "[CANCELLED] Setup cancelled." -ForegroundColor Yellow
        pause
        exit 0
    }

    Write-Host "[INFO] Removing existing task..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

# Create the scheduled task
Write-Host "[INFO] Creating scheduled task..." -ForegroundColor Cyan

# Define task action
$action = New-ScheduledTaskAction -Execute $batchFile -WorkingDirectory $projectRoot

# Define task trigger (daily at 2 AM)
$trigger = New-ScheduledTaskTrigger -Daily -At $taskTime

# Define task settings
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

# Define principal (run whether user is logged in or not)
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType S4U -RunLevel Highest

# Register the task
try {
    Register-ScheduledTask -TaskName $taskName `
                          -Description $taskDescription `
                          -Action $action `
                          -Trigger $trigger `
                          -Settings $settings `
                          -Principal $principal `
                          -Force | Out-Null

    Write-Host ""
    Write-Host "[OK] Scheduled task created successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Task Details:" -ForegroundColor Cyan
    Write-Host "  Name: $taskName" -ForegroundColor White
    Write-Host "  Schedule: Daily at midnight (12:00 AM)" -ForegroundColor White
    Write-Host "  Script: $batchFile" -ForegroundColor White
    Write-Host "  Logs: $projectRoot\logs\backup.log" -ForegroundColor White
    Write-Host ""
    Write-Host "The backup will run automatically every day at midnight" -ForegroundColor Green
    Write-Host ""

    # Test the task
    Write-Host "Would you like to run a test backup now? (yes/no): " -ForegroundColor Yellow -NoNewline
    $testResponse = Read-Host

    if ($testResponse -eq "yes") {
        Write-Host ""
        Write-Host "[INFO] Running test backup..." -ForegroundColor Cyan
        Start-ScheduledTask -TaskName $taskName
        Start-Sleep -Seconds 3

        # Show log
        $logFile = Join-Path $projectRoot "logs\backup.log"
        if (Test-Path $logFile) {
            Write-Host ""
            Write-Host "Last backup log:" -ForegroundColor Cyan
            Write-Host "-----------------------------------" -ForegroundColor Gray
            Get-Content $logFile -Tail 10
            Write-Host "-----------------------------------" -ForegroundColor Gray
        }

        Write-Host ""
        Write-Host "[OK] Test backup completed!" -ForegroundColor Green
    }

    Write-Host ""
    Write-Host "To manage this task:" -ForegroundColor Cyan
    Write-Host "  - Open Task Scheduler (taskschd.msc)" -ForegroundColor White
    Write-Host "  - Find 'MiniGolfDatabaseBackup' in Task Scheduler Library" -ForegroundColor White
    Write-Host ""

} catch {
    Write-Host ""
    Write-Host "[ERROR] Failed to create scheduled task!" -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Red
    Write-Host ""
    pause
    exit 1
}

pause
