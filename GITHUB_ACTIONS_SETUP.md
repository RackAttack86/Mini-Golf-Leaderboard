# GitHub Actions & Branch Protection Setup

## Overview

Two GitHub Actions workflows have been added to automatically test and scan for secrets on every commit:

1. **Tests Workflow** (`.github/workflows/test.yml`)
   - Runs full test suite on every push
   - Runs on pull requests to main/develop
   - Must pass before merge allowed

2. **Security Check Workflow** (`.github/workflows/security-check.yml`)
   - Scans for secrets in commits
   - Verifies .env is gitignored
   - Checks for hardcoded credentials
   - Must pass before merge allowed

## Enable Branch Protection (REQUIRED)

To enforce these checks, you need to enable branch protection on GitHub:

### Step 1: Go to Branch Protection Settings

1. Go to your repository: https://github.com/RackAttack86/Mini-Golf-Leaderboard
2. Click **Settings** (repository settings, not account settings)
3. Click **Branches** in the left sidebar
4. Under "Branch protection rules", click **Add rule** or **Add branch protection rule**

### Step 2: Configure Protection for Main Branch

**Branch name pattern:** `main`

**Enable these settings:**

#### Protect matching branches
- ✅ **Require a pull request before merging**
  - ✅ Require approvals: 1 (optional if you're the only developer)
  - ✅ Dismiss stale pull request approvals when new commits are pushed

- ✅ **Require status checks to pass before merging**
  - ✅ Require branches to be up to date before merging
  - **Add required status checks:**
    - ✅ `test` (from test.yml workflow)
    - ✅ `secret-scan` (from security-check.yml workflow)

- ✅ **Require conversation resolution before merging** (optional)

- ✅ **Do not allow bypassing the above settings** (recommended)

#### Rules applied to everyone including administrators
- ✅ **Include administrators** (recommended - even admins must follow rules)

**Click "Create" or "Save changes"**

### Step 3: Test the Workflow

The workflows will automatically run on your existing PR:
- Visit: https://github.com/RackAttack86/Mini-Golf-Leaderboard/pull/[YOUR_PR_NUMBER]
- Check the "Checks" tab to see workflow results
- Green checkmarks = tests passed, ready to merge
- Red X = tests failed, fix issues before merge

## How It Works

### When You Push Code

1. **Automatic Trigger:** GitHub Actions automatically runs when you:
   - Push commits to any branch
   - Create a pull request
   - Update an existing pull request

2. **Test Workflow Runs:**
   - Sets up Python 3.14
   - Installs all dependencies
   - Creates required directories
   - Runs full test suite (`pytest tests/`)
   - Reports results

3. **Security Workflow Runs:**
   - Scans git history for .env file
   - Checks for OAuth secrets (GOCSPX-*)
   - Checks for AWS keys
   - Checks for private keys
   - Verifies .env is in .gitignore
   - Scans for hardcoded passwords

4. **Merge Protection:**
   - If **ANY** workflow fails, merge is blocked
   - You must fix the issues and push again
   - Workflows re-run automatically on new push
   - Once all checks pass (green), merge button becomes available

## Viewing Workflow Results

### On Pull Request Page
1. Go to your PR: https://github.com/RackAttack86/Mini-Golf-Leaderboard/pull/[NUMBER]
2. Scroll down to see status checks
3. Click "Details" next to any check to see full logs

### On Actions Tab
1. Go to: https://github.com/RackAttack86/Mini-Golf-Leaderboard/actions
2. See all workflow runs
3. Click any run to see detailed logs
4. Click individual jobs to see step-by-step output

## Troubleshooting

### Tests Fail on GitHub but Pass Locally

**Common causes:**
- Missing dependencies in `requirements.txt`
- Environment differences (database, file paths)
- Tests depend on local files not in git

**Solution:**
- Check the workflow logs for specific errors
- Update `requirements.txt` if needed
- Ensure tests don't depend on local-only files

### Security Check Fails

**If secret scan fails:**
- Check what was detected in the workflow logs
- Remove any real secrets from commits
- Use `git filter-branch` or BFG Repo Cleaner to remove secrets from history
- Never commit real secrets - use environment variables

**If .env is detected:**
- Verify .env is in `.gitignore`
- Remove .env from git history if accidentally committed
- Use `.env.example` with placeholders only

### Workflow Doesn't Run

**Check these:**
1. Workflow files are in `.github/workflows/` directory
2. Files have `.yml` or `.yaml` extension
3. YAML syntax is valid
4. You have Actions enabled in repository settings

## GitHub Actions Pricing

- **Public repositories:** Unlimited free Actions minutes
- **Private repositories:** 2,000 free minutes/month (more than enough for this project)

Your workflows take ~2-5 minutes per run, so you won't hit limits.

## Customizing Workflows

### Change Python Version
Edit `.github/workflows/test.yml`:
```yaml
python-version: '3.14'  # Change to '3.13' or other version
```

### Add More Security Checks
Edit `.github/workflows/security-check.yml` to add custom patterns.

### Run Tests on Specific Branches Only
Edit `on:` section in `test.yml`:
```yaml
on:
  push:
    branches:
      - main
      - develop
      - 'feature/**'  # Only feature branches
```

## Summary

✅ **Workflows Added:**
- Automated testing on every push
- Security scanning on every push
- Blocks merge if tests fail
- Blocks merge if secrets detected

✅ **Next Steps:**
1. Enable branch protection on main branch (settings above)
2. Create your PR
3. Watch workflows run automatically
4. Merge when all checks pass (green checkmarks)

✅ **Benefits:**
- Catch bugs before they reach main
- Prevent secret leaks
- Ensure code quality
- Automated code review

---

**Now your repository has automated CI/CD with test and security enforcement!** 🎉
