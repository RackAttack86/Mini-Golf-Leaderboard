# Managing Secrets in Production (Fly.io)

## Overview

Your application is deployed on **Fly.io**. Environment variables and secrets are stored **securely in Fly.io's secrets manager**, NOT in the `fly.toml` file or in your code repository.

## Where Secrets Are Stored

### ❌ NOT in fly.toml
The `fly.toml` file is committed to Git and should **never** contain secrets. It only contains non-sensitive configuration like:
- `FLASK_ENV = "production"`
- `PORT = "8080"`
- `OAUTHLIB_INSECURE_TRANSPORT = "0"`

### ✅ In Fly.io Secrets Manager
Sensitive values like OAuth credentials are stored securely in Fly.io's encrypted secrets storage.

---

## How to Manage Secrets on Fly.io

### View Current Secrets

```bash
fly secrets list -a mini-golf-leaderboard
```

This will show you which secrets are set (but not their values, for security).

### Set OAuth Credentials (Required for Security Fixes)

```bash
# Set Google OAuth Client ID
fly secrets set GOOGLE_OAUTH_CLIENT_ID="your-client-id-here" -a mini-golf-leaderboard

# Set Google OAuth Client Secret
fly secrets set GOOGLE_OAUTH_CLIENT_SECRET="your-client-secret-here" -a mini-golf-leaderboard

# Set Flask Secret Key (if not already set)
fly secrets set SECRET_KEY="your-long-random-secret-key-here" -a mini-golf-leaderboard
```

**Note:** When you set a secret, Fly.io will automatically restart your application with the new environment variables.

### Set Multiple Secrets at Once

```bash
fly secrets set \
  GOOGLE_OAUTH_CLIENT_ID="your-client-id" \
  GOOGLE_OAUTH_CLIENT_SECRET="your-client-secret" \
  SECRET_KEY="your-secret-key" \
  -a mini-golf-leaderboard
```

### Remove a Secret

```bash
fly secrets unset GOOGLE_OAUTH_CLIENT_ID -a mini-golf-leaderboard
```

---

## Getting Your Google OAuth Credentials

If you don't have OAuth credentials set up yet:

1. **Go to Google Cloud Console:**
   - https://console.cloud.google.com/

2. **Create or Select a Project:**
   - Click "Select a project" → "New Project"
   - Name it (e.g., "Mini Golf Leaderboard")

3. **Enable Google+ API:**
   - Go to "APIs & Services" → "Library"
   - Search for "Google+ API"
   - Click "Enable"

4. **Create OAuth 2.0 Credentials:**
   - Go to "APIs & Services" → "Credentials"
   - Click "Create Credentials" → "OAuth client ID"
   - Application type: "Web application"
   - Name: "Mini Golf Leaderboard Production"

5. **Configure Redirect URIs:**
   Add both of these redirect URIs:
   ```
   https://mini-golf-leaderboard.fly.dev/login/google/authorized
   https://mini-golf-leaderboard.fly.dev/auth/google/callback
   ```
   (Replace `mini-golf-leaderboard.fly.dev` with your actual Fly.io domain)

6. **Copy Credentials:**
   - Copy the "Client ID"
   - Copy the "Client Secret"

7. **Set Secrets in Fly.io:**
   ```bash
   fly secrets set \
     GOOGLE_OAUTH_CLIENT_ID="paste-client-id-here" \
     GOOGLE_OAUTH_CLIENT_SECRET="paste-client-secret-here" \
     -a mini-golf-leaderboard
   ```

---

## Verifying Secrets Are Set

### Check if secrets are configured:
```bash
fly secrets list -a mini-golf-leaderboard
```

Expected output:
```
NAME                          DIGEST         CREATED AT
GOOGLE_OAUTH_CLIENT_ID        abc123...      2024-01-10T...
GOOGLE_OAUTH_CLIENT_SECRET    def456...      2024-01-10T...
SECRET_KEY                    ghi789...      2024-01-10T...
```

### Check application logs:
```bash
fly logs -a mini-golf-leaderboard
```

Look for startup messages confirming OAuth is configured.

---

## Security Best Practices

### ✅ DO:
- Store all secrets in Fly.io secrets manager
- Use strong, randomly generated `SECRET_KEY` (at least 32 characters)
- Rotate secrets periodically
- Use different OAuth credentials for staging and production

### ❌ DON'T:
- Never commit secrets to Git
- Never put secrets in `fly.toml`
- Never put secrets in `.env` files that are committed to Git
- Never log secret values

---

## Deploying the Security Fixes

After setting the secrets, deploy the updated code:

1. **Ensure secrets are set:**
   ```bash
   fly secrets list -a mini-golf-leaderboard
   ```

2. **Deploy the security fixes:**
   ```bash
   fly deploy -a mini-golf-leaderboard
   ```

3. **Monitor deployment:**
   ```bash
   fly logs -a mini-golf-leaderboard
   ```

4. **Test OAuth flow:**
   - Visit: https://mini-golf-leaderboard.fly.dev/auth/login
   - Click "Sign in with Google"
   - Verify OAuth state validation is working

---

## Troubleshooting

### OAuth Error: "redirect_uri_mismatch"

**Cause:** The redirect URI in your Google Cloud Console doesn't match your Fly.io domain.

**Fix:** Add these URIs to Google Cloud Console:
```
https://mini-golf-leaderboard.fly.dev/login/google/authorized
https://mini-golf-leaderboard.fly.dev/auth/google/callback
```

### OAuth Error: "invalid_client"

**Cause:** Secrets aren't set or are incorrect.

**Fix:**
1. Verify secrets are set: `fly secrets list -a mini-golf-leaderboard`
2. Re-set secrets with correct values
3. Check logs: `fly logs -a mini-golf-leaderboard`

### Application won't start after setting secrets

**Check logs:**
```bash
fly logs -a mini-golf-leaderboard
```

Look for error messages about missing configuration.

---

## Environment Variables vs Secrets

### Public Environment Variables (in fly.toml)
These can be in your Git repository:
- `FLASK_ENV = "production"`
- `PORT = "8080"`
- `OAUTHLIB_INSECURE_TRANSPORT = "0"`

### Secrets (in Fly.io secrets manager)
These must NEVER be in Git:
- `GOOGLE_OAUTH_CLIENT_ID`
- `GOOGLE_OAUTH_CLIENT_SECRET`
- `SECRET_KEY`

---

## Summary

**Your OAuth credentials are stored in Fly.io's secrets manager, NOT in your code repository.**

To set them:
```bash
fly secrets set \
  GOOGLE_OAUTH_CLIENT_ID="your-client-id" \
  GOOGLE_OAUTH_CLIENT_SECRET="your-client-secret" \
  -a mini-golf-leaderboard
```

To verify:
```bash
fly secrets list -a mini-golf-leaderboard
```

To deploy security fixes:
```bash
fly deploy -a mini-golf-leaderboard
```

---

## Important: fly.toml Security Fix

⚠️ **The `fly.toml` file has been updated to remove `OAUTHLIB_RELAX_TOKEN_SCOPE`** which was a critical security vulnerability.

Before deploying, make sure to commit this change:
```bash
git add fly.toml
git commit -m "Security: Remove OAUTHLIB_RELAX_TOKEN_SCOPE from production config"
```

This ensures the security fixes are applied in production.
