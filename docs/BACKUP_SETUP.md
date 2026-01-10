# Synology NAS Backup Setup Guide

This guide will help you set up automated weekly backups from your Fly.io app to your Synology NAS.

## Overview

The GitHub Action (`backup-to-nas.yml`) will:
- ✅ Run every Sunday at 3 AM UTC (or manually via GitHub Actions UI)
- ✅ Create a compressed backup of your database and photos on Fly.io
- ✅ Download the backup to GitHub Actions runner
- ✅ Upload the backup to your Synology NAS via SCP/SSH
- ✅ Keep the last 8 weekly backups (auto-delete older ones)
- ✅ Clean up temporary files

## Prerequisites

- Synology NAS accessible from the internet (or via VPN/tunnel)
- SSH access enabled on your Synology NAS
- A folder on your NAS for backups

---

## Step 1: Enable SSH on Synology NAS

1. Log in to your Synology DSM (web interface)
2. Go to **Control Panel** → **Terminal & SNMP**
3. Check **Enable SSH service**
4. Set SSH port (default: 22, or custom like 2222)
5. Click **Apply**

---

## Step 2: Create a Backup User on Synology (Recommended)

For security, create a dedicated user for backups:

1. Go to **Control Panel** → **User & Group**
2. Click **Create** → **Create User**
3. Username: `backup-user` (or your choice)
4. Password: Create a strong password (you won't need to remember it - we'll use SSH keys)
5. Skip email and groups
6. **Permissions**:
   - Give read/write access to the shared folder where you want backups
   - No admin rights needed
7. **Applications**: Deny all
8. Click **Apply**

---

## Step 3: Create Backup Directory on NAS

1. Open **File Station**
2. Navigate to a shared folder (e.g., `homes` or create a new one called `backups`)
3. Create a folder: `minigolf-backups`
4. Note the full path: `/volume1/homes/backup-user/minigolf-backups` (example)

To find the exact path, SSH into your NAS and run:
```bash
ssh admin@YOUR_NAS_IP
pwd  # Shows current directory
cd /volume1/homes/backup-user/minigolf-backups  # Navigate to your backup folder
pwd  # This is the path you'll need
```

---

## Step 4: Generate SSH Key Pair

On your local computer (Windows PowerShell, Mac/Linux terminal):

```bash
# Generate SSH key (no passphrase - GitHub Actions needs this)
ssh-keygen -t ed25519 -f ~/.ssh/nas_backup_key -N ""

# This creates two files:
# - ~/.ssh/nas_backup_key (private key - keep secret!)
# - ~/.ssh/nas_backup_key.pub (public key - goes on NAS)
```

**View the private key** (you'll need this for GitHub):
```bash
cat ~/.ssh/nas_backup_key
```

**View the public key** (you'll need this for the NAS):
```bash
cat ~/.ssh/nas_backup_key.pub
```

---

## Step 5: Add Public Key to Synology NAS

### Option A: Via SSH (Easiest)

```bash
# SSH into your NAS
ssh admin@YOUR_NAS_IP

# Switch to the backup user
sudo -i -u backup-user

# Create .ssh directory if it doesn't exist
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# Add your public key to authorized_keys
echo "YOUR_PUBLIC_KEY_CONTENT_HERE" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys

# Exit
exit
exit
```

### Option B: Via DSM File Station

1. Enable showing hidden files: **Settings** → **Show hidden files**
2. Navigate to `homes/backup-user/`
3. Create folder `.ssh` (with the dot)
4. Upload a file named `authorized_keys` containing your public key
5. SSH in and run:
   ```bash
   chmod 700 ~/.ssh
   chmod 600 ~/.ssh/authorized_keys
   chown backup-user:users ~/.ssh/authorized_keys
   ```

---

## Step 6: Test SSH Connection

From your local computer:

```bash
ssh -i ~/.ssh/nas_backup_key backup-user@YOUR_NAS_IP

# If it works without asking for a password, you're good!
# Try creating a test file:
touch minigolf-backups/test.txt
ls minigolf-backups/
exit
```

---

## Step 7: Add GitHub Secrets

Go to your GitHub repository: **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Add these 4 secrets:

### 1. `NAS_SSH_KEY`
- **Value**: The **entire private key** from Step 4
- Copy everything from `cat ~/.ssh/nas_backup_key`, including:
  ```
  -----BEGIN OPENSSH PRIVATE KEY-----
  ...
  -----END OPENSSH PRIVATE KEY-----
  ```

### 2. `NAS_HOST`
- **Value**: Your NAS IP address or domain
- Examples:
  - `192.168.1.100` (local IP)
  - `nas.yourdomain.com` (if you have DDNS)
  - `your-nas-ip.synology.me` (QuickConnect domain)

### 3. `NAS_USER`
- **Value**: `backup-user` (or whatever username you created)

### 4. `NAS_BACKUP_PATH`
- **Value**: Full path to backup directory on NAS
- Example: `/volume1/homes/backup-user/minigolf-backups`

---

## Step 8: Test the Backup Workflow

1. Go to your GitHub repository
2. Click **Actions** tab
3. Select **Weekly Backup to Synology NAS**
4. Click **Run workflow** → **Run workflow** (manual trigger)
5. Wait for the workflow to complete (~1-2 minutes)
6. Check your NAS `minigolf-backups` folder for the backup file

Expected filename format: `minigolf-backup-20260109-123456.tar.gz`

---

## Step 9: Verify Backup Contents

To verify what's in a backup:

```bash
# On your NAS or local computer
tar -tzf minigolf-backup-20260109-123456.tar.gz

# Should show:
# minigolf.db
# round_pictures/
# round_pictures/photo1.jpg
# round_pictures/photo2.jpg
# ...
```

To restore a backup:

```bash
# Extract
tar -xzf minigolf-backup-20260109-123456.tar.gz

# You'll get:
# - minigolf.db (your database)
# - round_pictures/ (folder with all photos)
```

---

## Troubleshooting

### "Permission denied (publickey)"
- Make sure the private key is correctly added to GitHub Secrets
- Verify `~/.ssh/authorized_keys` on NAS has correct permissions (600)
- Check NAS SSH is enabled on the port you're using

### "No such file or directory" when uploading
- Double-check `NAS_BACKUP_PATH` secret matches the actual path on your NAS
- Create the directory if it doesn't exist

### "Connection timed out"
- If NAS is behind a router, you may need:
  - Port forwarding for SSH port
  - VPN/Tailscale connection
  - Dynamic DNS (DDNS) if your IP changes

### "Host key verification failed"
- The workflow includes `StrictHostKeyChecking=no` to avoid this
- If still failing, check NAS firewall settings

---

## Security Considerations

✅ **Good practices:**
- Using SSH keys instead of passwords
- Dedicated backup user with minimal permissions
- Auto-cleanup keeps only 8 weeks of backups (saves space)
- Private key stored as GitHub Secret (encrypted)

⚠️ **Recommendations:**
- Use a non-standard SSH port (not 22) if exposing NAS to internet
- Enable Synology's firewall and only allow GitHub Actions IPs (if possible)
- Consider using Tailscale/VPN for added security
- Regularly test restoring from backups

---

## Schedule

- **Automatic backups**: Every Sunday at 3 AM UTC
- **Retention**: Last 8 weekly backups (2 months)
- **Manual backup**: Anytime via GitHub Actions UI

To change the schedule, edit `.github/workflows/backup-to-nas.yml`:
```yaml
schedule:
  - cron: '0 3 * * 0'  # Sunday 3 AM UTC
  # Minutes Hour Day Month DayOfWeek
  # Examples:
  # '0 2 * * *'   = Every day at 2 AM
  # '0 0 * * 1'   = Every Monday at midnight
  # '0 4 1 * *'   = First day of month at 4 AM
```

---

## Cost

- ✅ **Free** - GitHub Actions gives 2,000 minutes/month for private repos
- ✅ Each backup takes ~1-2 minutes
- ✅ 52 backups/year × 2 minutes = ~104 minutes/year

---

## What Gets Backed Up

✅ **Included:**
- `minigolf.db` - Your SQLite database with all players, courses, rounds, scores
- `round_pictures/` - All uploaded game photos

❌ **Not included:**
- Application code (already in GitHub)
- Log files (temporary)
- Flask session files (temporary)

---

## Questions?

If you run into issues, check the GitHub Actions logs for detailed error messages.
