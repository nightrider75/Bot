# ⚠️ Important Fix - Cloud Run PORT Environment Variable

## Issue
Cloud Run deployment failed with:
```
ERROR: (gcloud.run.deploy) spec.template.spec.containers[0].env: The following reserved env names were provided: PORT. These values are automatically set by the system.
```

## Root Cause
Cloud Run **automatically sets** the `PORT` environment variable. You cannot override it with `--set-env-vars`.

## Solution Applied ✅

Updated `.github/workflows/deploy-cloud-run.yml` to **remove** `PORT` from the environment variables:

### ❌ Wrong (causes error):
```yaml
--set-env-vars "PORT=8080,WORKERS=4"
```

### ✅ Correct:
```yaml
--set-env-vars "WORKERS=4,ENV_FILE=${{ secrets.CLOUD_RUN_ENV_FILE }}"
```

The `--port 8080` flag tells Cloud Run which port your container listens on, and Cloud Run will automatically set `PORT=8080` as an environment variable inside your container.

## How Your App Gets the PORT

Your application reads `PORT` from the environment (set by Cloud Run automatically):

```python
# In src/bot/config.py
class Settings(BaseSettings):
    port: int = 8080  # Default, but Cloud Run's PORT env var takes precedence
```

## Updated Deployment Command

```bash
gcloud run deploy $SERVICE_NAME \
  --image $IMAGE_TAG \
  --region $REGION \
  --platform managed \
  --port 8080 \                    # Tell Cloud Run which port to route to
  --timeout 300 \
  --memory 2Gi \
  --cpu 2 \
  --min-instances 0 \
  --max-instances 10 \
  --allow-unauthenticated \
  --set-env-vars "WORKERS=4,ENV_FILE=$CLOUD_RUN_ENV_FILE"  # No PORT here!
```

## Next Steps

1. ✅ Fix has been applied to `.github/workflows/deploy-cloud-run.yml`
2. Commit and push:
   ```bash
   git add .
   git commit -m "fix: remove PORT from env vars (Cloud Run sets it automatically)"
   git push origin main
   ```
3. Monitor the deployment in GitHub Actions

## Cloud Run Reserved Environment Variables

Cloud Run automatically sets these environment variables (do NOT set them manually):
- `PORT` - The port your container should listen on
- `K_SERVICE` - The name of the Cloud Run service
- `K_REVISION` - The name of the Cloud Run revision
- `K_CONFIGURATION` - The name of the Cloud Run configuration

You can reference these in your app, but don't try to override them!
