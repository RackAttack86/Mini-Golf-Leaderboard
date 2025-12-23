# Deployment Guide

This guide covers deploying the Mini Golf Leaderboard to your NAS for network access.

## Option 1: Docker Deployment (Recommended)

### Prerequisites
- Docker installed on your NAS (Synology, QNAP, etc.)
- SSH or terminal access to your NAS

### Steps

1. **Transfer files to your NAS:**
```bash
# Use SCP, SFTP, or your NAS's file manager to upload the project
scp -r Mini-Golf-Leaderboard user@nas-ip:/path/to/apps/
```

2. **SSH into your NAS:**
```bash
ssh user@nas-ip
cd /path/to/apps/Mini-Golf-Leaderboard
```

3. **Set up data directory:**
```bash
cp -r data-example data
```

4. **Build and run with Docker Compose:**
```bash
docker-compose up -d
```

5. **Access the app:**
- Open browser to `http://nas-ip:5001`
- Your friends can access via `http://your-nas-ip:5001` on your local network

### Docker Commands
```bash
# View logs
docker-compose logs -f

# Restart
docker-compose restart

# Stop
docker-compose down

# Rebuild after code changes
docker-compose up -d --build
```

## Option 2: Direct Python Deployment

### Prerequisites
- Python 3.12+ installed on your NAS
- SSH access

### Steps

1. **Transfer and setup:**
```bash
# Transfer files
scp -r Mini-Golf-Leaderboard user@nas-ip:/path/to/apps/

# SSH in
ssh user@nas-ip
cd /path/to/apps/Mini-Golf-Leaderboard

# Setup data
cp -r data-example data

# Install dependencies
pip install -r requirements.txt
```

2. **Run with Gunicorn:**
```bash
# Production mode
FLASK_ENV=production gunicorn --bind 0.0.0.0:5001 --workers 4 app:app
```

3. **Keep it running (use systemd or screen):**

**Using screen:**
```bash
screen -S minigolf
FLASK_ENV=production gunicorn --bind 0.0.0.0:5001 --workers 4 app:app
# Press Ctrl+A, then D to detach
# Reattach with: screen -r minigolf
```

**Using systemd (if available):**
Create `/etc/systemd/system/minigolf.service`:
```ini
[Unit]
Description=Mini Golf Leaderboard
After=network.target

[Service]
User=your-user
WorkingDirectory=/path/to/Mini-Golf-Leaderboard
Environment="FLASK_ENV=production"
ExecStart=/usr/bin/gunicorn --bind 0.0.0.0:5001 --workers 4 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl enable minigolf
sudo systemctl start minigolf
```

## Security Considerations

### 1. Local Network Only (Recommended for friends)
- By default, the app is accessible on your local network only
- Share your NAS's local IP with friends: `http://192.168.x.x:5001`
- No port forwarding needed - safer!

### 2. Internet Access (if needed)
If you want friends outside your network to access:
- Set up port forwarding on your router (port 5001)
- Use dynamic DNS service for a stable URL
- **Strongly recommended:** Add authentication or use a reverse proxy with HTTPS

### 3. Change Secret Key
For production, set a secure SECRET_KEY:
```bash
# Generate a random key
python -c "import secrets; print(secrets.token_hex(32))"

# Set it in docker-compose.yml:
environment:
  - FLASK_ENV=production
  - SECRET_KEY=your-generated-key-here
```

## Reverse Proxy with Nginx (Optional)

If your NAS has Nginx, you can use it as a reverse proxy:

```nginx
server {
    listen 80;
    server_name minigolf.local;

    location / {
        proxy_pass http://localhost:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /static {
        alias /path/to/Mini-Golf-Leaderboard/static;
    }
}
```

## Synology-Specific Instructions

1. **Enable Docker:**
   - Open Package Center
   - Install "Docker" package

2. **Upload via File Station:**
   - Upload project to `/docker/minigolf/`

3. **Use Container Manager:**
   - Go to Docker → Project
   - Create new project
   - Select the folder with docker-compose.yml
   - Click "Build"

4. **Port Configuration:**
   - The app will be available on port 5001
   - Or configure reverse proxy in Control Panel → Application Portal

## QNAP-Specific Instructions

1. **Enable Container Station:**
   - Install from App Center

2. **Upload files:**
   - Upload to `/share/Container/minigolf/`

3. **Create container:**
   - Open Container Station
   - Create → Create Application
   - Select docker-compose.yml
   - Start

## Accessing from Different Devices

Once deployed, your friends can access via:
- **Same network:** `http://nas-ip:5001`
- **With dynamic DNS:** `http://yourdomain.ddns.net:5001`
- **With reverse proxy:** `http://minigolf.yourdomain.com`

## Data Backup

Your data is in the `data/` directory. To backup:

```bash
# Using Docker
docker-compose down
cp -r data data-backup-$(date +%Y%m%d)

# Or backup from host
tar -czf minigolf-backup-$(date +%Y%m%d).tar.gz data/
```

## Troubleshooting

### Can't access from other devices
- Check firewall on NAS
- Verify port 5001 is not blocked
- Try accessing from NAS: `curl http://localhost:5001`

### Permission errors
```bash
# Fix data directory permissions
chmod -R 755 data/
```

### View logs
```bash
# Docker
docker-compose logs -f

# Direct deployment
# Logs will be in terminal where gunicorn is running
```

## Performance Tips

- **Workers:** 2-4 workers is good for a NAS (adjust in Dockerfile)
- **Memory:** App uses ~50-100MB per worker
- **Storage:** Minimal - JSON files are very small

## Updates

To update the application:

```bash
# Pull latest code
git pull

# Docker
docker-compose up -d --build

# Direct
pip install -r requirements.txt
# Restart gunicorn
```
