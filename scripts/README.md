# Database Management Scripts

This directory contains utility scripts for managing the SQLite database.

## Backup Database

Creates a timestamped backup of the database:

```bash
python scripts/backup_database.py
```

**What it does:**
- Creates a backup in `data/backups/minigolf_backup_YYYYMMDD_HHMMSS.db`
- Automatically keeps only the last 10 backups
- Shows backup size and location

**When to use:**
- Before major changes to the database
- Before running migrations
- Regularly (recommended: weekly or before each deployment)

## Restore Database

Restores the database from a backup:

```bash
python scripts/restore_database.py
```

**What it does:**
- Lists all available backups with timestamps
- Prompts you to select which backup to restore
- Creates a safety backup of current database before restoring
- Restores the selected backup

**When to use:**
- After data loss or corruption
- To roll back unwanted changes
- For testing purposes

## Manual Backup (Quick)

For a quick manual backup without running scripts:

```bash
# Windows
copy data\minigolf.db data\minigolf_backup_%date:~-4,4%%date:~-10,2%%date:~-7,2%.db

# Linux/Mac
cp data/minigolf.db "data/minigolf_backup_$(date +%Y%m%d).db"
```

## Automated Backups (Recommended)

### Windows Task Scheduler

1. Open Task Scheduler
2. Create Basic Task
3. Name: "Mini Golf DB Backup"
4. Trigger: Daily or Weekly
5. Action: Start a program
6. Program: `python`
7. Arguments: `D:\Mini-Golf-Leaderboard\scripts\backup_database.py`
8. Start in: `D:\Mini-Golf-Leaderboard`

### Linux/Mac Cron Job

Add to crontab:
```bash
# Backup every day at 2 AM
0 2 * * * cd /path/to/Mini-Golf-Leaderboard && python scripts/backup_database.py
```

## Cloud Backup (Best Practice)

For maximum safety, also backup to cloud storage:

1. **Google Drive / Dropbox / OneDrive**: Set `data/backups/` folder to sync
2. **GitHub**: Commit backups periodically (be careful with .gitignore)
3. **AWS S3 / Azure Blob**: Use cloud storage services

## Emergency Recovery

If you lose the database completely:

1. Check `data/backups/` for automatic backups
2. Check cloud sync folders (Google Drive, etc.)
3. Check Git history (if database was committed)
4. Use `restore_database.py` to restore from any backup

## Database Information

- **Current database**: `data/minigolf.db`
- **Current size**: ~200 KB
- **Tables**: players, courses, rounds, round_scores, achievements, player_achievements, course_ratings, course_notes, personal_bests, tournaments, tournament_rounds
- **Growth rate**: ~1-2 KB per round added
