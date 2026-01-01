# Cloud Run Container Startup Fix - Step by Step

## Current Issue
Container fails to start with:
```
ERROR: The user-provided container failed to start and listen on the port defined provided by the PORT=8080 environment variable within the allocated timeout.
```

## Root Cause Analysis

Based on the screenshot of your GitHub ENV_FILE secret, the issue is:

**Your ENV_FILE contains `PORT=8080` which conflicts with Cloud Run's PORT setting.**

## Step-by-Step Fix

### Step 1: Fix the ENV_FILE Secret (CRITICAL)

1. Go to: https://github.com/nightrider75/Bot/settings/environments
2. Click on **"production"** environment
3. Find **ENV_FILE** in the list
4. Click the **pencil/edit icon**
5. **Remove these lines** from the value:
   ```
   PORT=8080
   WORKERS=4
   ```
6. Click **"Update variable"**

**Why?** 
- Cloud Run sets `PORT` automatically via environment variable
- We set `WORKERS` via the deployment command
- Having them in ENV_FILE creates conflicts

### Step 2: Verify Your ENV_FILE Should Look Like

```env
# App Config (DO NOT include PORT or WORKERS here!)
BASE_URL_DOMAIN=https://bot-54147607218-europe-west1.run.app

# Auth Config
AUTH_USERNAME=admin
AUTH_PASSWORD=admin

# Pipeline Config
PIPELINE_CONFIG__AUDIO_RECORDING=True
PIPELINE_CONFIG__USER_IDLE_ENABLED=True
...rest of your config...
```

### Step 3: Code Changes (Already Applied)

✅ Updated `src/bot/app.py` to:
- Read PORT from environment variable first (Cloud Run's PORT)
- Fall back to settings.port if not set
- Added detailed logging

✅ Updated `src/bot/config.py` to:
- Ensure environment variables take precedence over .env file
- Added proper encoding and case sensitivity

✅ Updated deployment to use `WORKERS=1`:
- Cloud Run scales horizontally (multiple containers)
- Each container should run 1 worker
- This is more stable than multiple workers per container

### Step 4: Commit and Push

```bash
git add .
git commit -m "fix: properly handle PORT from Cloud Run environment"
git push origin main
```

### Step 5: Monitor Deployment

Watch the logs at: https://github.com/nightrider75/Bot/actions

Look for these startup messages:
```
[STARTUP] Starting bot orchestration service...
[STARTUP] PORT=8080
[STARTUP] WORKERS=1
[STARTUP] Creating .env file from ENV_FILE environment variable
[STARTUP] .env file created successfully
[STARTUP] Launching application...
[STARTUP] Bot app module loading...
[STARTUP] Environment PORT=8080
[STARTUP] Settings PORT=8080
[STARTUP] Workers=1
```

## Understanding the Fix

### How PORT Works in Cloud Run:

1. **Cloud Run sets `PORT` environment variable** → e.g., `PORT=8080`
2. **Our entrypoint script creates `.env` from `ENV_FILE`** → Should NOT contain PORT
3. **Python loads settings:**
   - First checks environment variables (finds PORT=8080 from Cloud Run) ✅
   - Then checks .env file (no PORT there) ✅
   - Uses environment variable value (8080) ✅
4. **app.py explicitly reads from environment** → `os.environ.get('PORT')`
5. **Uvicorn listens on that port** → `port=8080`

### What Was Wrong Before:

```
Cloud Run: PORT=8080 (environment variable)
.env file: PORT=8080 (from ENV_FILE)
           ↓
Conflict! Which one to use?
           ↓
Container fails to start
```

### What's Right Now:

```
Cloud Run: PORT=8080 (environment variable) ✅
.env file: (no PORT) ✅
           ↓
Clear! Use environment variable
           ↓
Container starts successfully
```

## Troubleshooting

### If it still fails after fixing ENV_FILE:

1. **Check the actual Cloud Run logs:**
   ```bash
   gcloud logging tail "resource.type=cloud_run_revision" \
     --project=YOUR_PROJECT_ID \
     --format=json
   ```

2. **Test locally with exact Cloud Run setup:**
   ```bash
   # Create ENV_FILE without PORT or WORKERS
   cat > test_env_file.txt << 'EOF'
   BASE_URL_DOMAIN=localhost:8080
   AUTH_USERNAME=admin
   AUTH_PASSWORD=admin
   # ...rest of your config WITHOUT PORT or WORKERS
   EOF
   
   # Build and run
   docker build -t bot-test .
   docker run -p 8080:8080 \
     -e PORT=8080 \
     -e WORKERS=1 \
     -e ENV_FILE="$(cat test_env_file.txt)" \
     bot-test
   
   # Test
   curl http://localhost:8080/health
   ```

3. **Check for other startup errors:**
   - Database connection failures
   - Missing API keys
   - Invalid configuration values

### Common Issues:

**Database connection timeout:**
- Cloud Run might not be able to reach your database
- Solution: Use Cloud SQL Proxy or make database publicly accessible with SSL

**Missing required env vars:**
- Check logs for Pydantic validation errors
- Ensure all required config is in ENV_FILE

**Memory issues:**
- Initial deployment might need more memory
- Try `--memory 4Gi` temporarily

## Deployment Command Reference

After fixing ENV_FILE, this is what runs:

```bash
gcloud run deploy $SERVICE_NAME \
  --image $IMAGE_TAG \
  --region $REGION \
  --platform managed \
  --port 8080 \                    # Tell Cloud Run which port to route to
  --timeout 300 \                   # 5 minutes for startup
  --memory 2Gi \                    # 2GB memory
  --cpu 2 \                         # 2 vCPUs
  --min-instances 0 \               # Scale to zero when idle
  --max-instances 10 \              # Max 10 containers
  --allow-unauthenticated \         # Public access
  --set-env-vars "WORKERS=1,ENV_FILE=<your env file WITHOUT port>"
```

Cloud Run automatically adds:
- `PORT=8080` environment variable
- `K_SERVICE=your-service-name`
- `K_REVISION=your-revision`
- `K_CONFIGURATION=your-config`

## Success Criteria

Deployment is successful when you see:

1. ✅ GitHub Actions completes without errors
2. ✅ Health check returns: `{"status": "healthy", ...}`
3. ✅ Cloud Run logs show:
   ```
   [STARTUP] Starting bot orchestration service...
   [STARTUP] PORT=8080
   [STARTUP] Environment PORT=8080
   INFO:     Started server process
   INFO:     Waiting for application startup.
   INFO:     Application startup complete.
   INFO:     Uvicorn running on http://0.0.0.0:8080
   ```

## Next Steps After Successful Deployment

1. Test your endpoints
2. Monitor metrics in Cloud Console
3. Set up Cloud Monitoring alerts
4. Configure custom domain (optional)
5. Enable Cloud Armor for DDoS protection (optional)
6. Set up Continuous Delivery from main branch
