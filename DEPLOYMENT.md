# Deployment Guide

This guide covers deploying the Mini Golf Leaderboard to your NAS for network access.

## Prerequisites: Google OAuth Setup

The application requires Google OAuth for authentication. Set this up before deployment:

### 1. Create Google OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the **Google+ API**:
   - Navigate to "APIs & Services" → "Library"
   - Search for "Google+ API" and enable it
4. Create OAuth 2.0 credentials:
   - Go to "APIs & Services" → "Credentials"
   - Click "Create Credentials" → "OAuth 2.0 Client ID"
   - Application type: "Web application"
   - Name: "Mini Golf Leaderboard"

### 2. Configure Authorized Redirect URIs

Add these redirect URIs based on your deployment:

**For HTTPS deployment (recommended):**
```
https://your-domain.com/login/google/authorized
```

**For local network (HTTP):**
```
http://your-nas-ip:8080/login/google/authorized
```

**For development/testing:**
```
http://localhost:5001/login/google/authorized
```

### 3. Save Your Credentials

Copy the **Client ID** and **Client Secret** - you'll need these for the `.env.production` file.

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

3. **Configure production environment:**
```bash
# Copy the production environment template
cp .env.production.example .env.production

# Generate a secure secret key
python3 -c "import secrets; print(secrets.token_hex(32))"

# Edit .env.production with your values
nano .env.production
```

Update `.env.production` with:
- Your generated SECRET_KEY
- Google OAuth CLIENT_ID
- Google OAuth CLIENT_SECRET

4. **Set up data directory:**
```bash
# If deploying for the first time
cp -r data-example data

# If you have existing data, ensure it's in the data/ directory
```

5. **Build and run with Docker Compose:**
```bash
docker-compose up -d --build
```

6. **Set up admin user:**
```bash
# Run the admin setup script inside the container
docker exec -it mini-golf-leaderboard python setup_admin.py

# Follow the prompts to promote a player to admin
```

7. **Access the app:**
- Open browser to `http://nas-ip:8080`
- Click "Login" and sign in with Google
- Link your Google account to your player profile
- Your friends can access via `http://your-nas-ip:8080` on your local network

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

### 1. Authentication & Authorization
- **Google OAuth:** All users must sign in with Google accounts
- **Account Linking:** Google accounts are linked to player profiles
- **Role-Based Access:**
  - Regular players: Can add rounds, edit own profile, view stats
  - Admins: Can manage all courses, players, and rounds
- First admin must be set up using `setup_admin.py` script

### 2. Production Security Settings
The app automatically enforces security in production (`FLASK_ENV=production`):
- **HTTPS Required:** OAuth will only work over HTTPS (except on local network)
- **Secure Cookies:** Session cookies set with httponly and secure flags
- **Open Redirect Protection:** URL validation prevents redirect attacks
- **Secret Key:** Strong random key required (see setup steps)

### 3. Local Network Only (Recommended)
- By default, the app is accessible on your local network only
- Share your NAS's local IP with friends: `http://192.168.x.x:8080`
- No port forwarding needed - safer!
- **Note:** Google OAuth works on local network with proper redirect URI configuration

### 4. Internet Access (Advanced)
If you want friends outside your network to access:
- **HTTPS is REQUIRED** for OAuth to work over the internet
- Set up port forwarding on your router (port 8080)
- Use dynamic DNS service for a stable URL
- **Must have:** Valid SSL certificate (Let's Encrypt recommended)
- Configure reverse proxy with HTTPS (see Nginx section below)
- Add your public domain to Google OAuth authorized redirect URIs

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

### Authentication Issues

**"OAuth callback error" or "redirect_uri_mismatch":**
- Check that your redirect URI in Google Cloud Console exactly matches:
  - `http://your-nas-ip:8080/login/google/authorized` (for local network)
  - `https://your-domain.com/login/google/authorized` (for HTTPS)
- Make sure the protocol (http/https) matches
- Verify the port number is correct (8080 for production, 5001 for dev)

**"Can't sign in" or "Google authentication failed":**
- Verify Google+ API is enabled in Google Cloud Console
- Check that GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET are set correctly in `.env.production`
- View logs: `docker-compose logs -f` to see detailed error messages

**"No players available to link":**
- All players already have Google accounts linked
- Create a new player first, then link your Google account
- Or ask an admin to unlink an account

**"Unauthorized" after login:**
- Check if you're trying to access an admin-only route
- Verify your player has the correct role: `docker exec -it mini-golf-leaderboard python setup_admin.py`

### Can't access from other devices
- Check firewall on NAS
- Verify port 8080 is not blocked
- Try accessing from NAS: `curl http://localhost:8080`

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

### Environment variable issues
```bash
# Check if variables are loaded in container
docker exec -it mini-golf-leaderboard env | grep -E 'GOOGLE|SECRET|FLASK'

# Verify .env.production exists and has correct values
cat .env.production
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
