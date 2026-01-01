# Cloud Run Deployment Checklist

## ✅ Pre-Deployment Checklist

### Code Changes (Already Done)
- [x] Updated Dockerfile with proper entrypoint script
- [x] Added `/health` endpoint to application
- [x] Added startup logging for diagnostics
- [x] Fixed configuration defaults
- [x] Updated GitHub Actions workflow with proper Cloud Run flags

### GitHub Secrets (ACTION REQUIRED)
- [ ] Add `CLOUD_RUN_ENV_FILE` secret to GitHub
  - Go to: Repository → Settings → Secrets and variables → Actions
  - Click "New repository secret"
  - Name: `CLOUD_RUN_ENV_FILE`
  - Value: Entire contents of `.env` file

### Existing Secrets (Verify)
- [ ] `GCP_PROJECT_ID` - Your GCP project ID
- [ ] `GCP_SERVICE_NAME` - Cloud Run service name
- [ ] `GCP_REGION` - GCP region (e.g., us-central1)
- [ ] `GCP_ARTIFACT_REGISTRY_REPO` - Artifact Registry repository name
- [ ] `GCP_SA_KEY` - Service account JSON key

## 🚀 Deployment Methods

### Method 1: Deploy via GitHub Actions (Recommended)

1. **Add the GitHub Secret** (see above)
2. **Commit and push** the changes:
   ```bash
   git add .
   git commit -m "fix: Cloud Run deployment configuration"
   git push origin main
   ```
3. **Monitor the deployment**:
   - Go to GitHub → Actions tab
   - Watch the "Deploy to Cloud Run" workflow
   - Check for successful completion

### Method 2: Deploy Manually Using Script

1. **Set environment variables**:
   ```bash
   export PROJECT_ID="your-gcp-project-id"
   export REGION="us-central1"
   export SERVICE_NAME="your-service-name"
   export REPOSITORY="your-artifact-registry-repo"
   ```

2. **Run the deployment script**:
   ```bash
   ./deploy-to-cloud-run.sh
   ```

### Method 3: Deploy Manually with gcloud

```bash
# Set variables
PROJECT_ID="your-project-id"
REGION="us-central1"
SERVICE_NAME="your-service-name"
REPOSITORY="your-repo-name"
COMMIT_SHA=$(git rev-parse HEAD)
IMAGE_TAG="$REGION-docker.pkg.dev/$PROJECT_ID/$REPOSITORY/$SERVICE_NAME:$COMMIT_SHA"

# Build and push
docker build -t $IMAGE_TAG .
gcloud auth configure-docker $REGION-docker.pkg.dev --quiet
docker push $IMAGE_TAG

# Deploy with proper configuration
gcloud run deploy $SERVICE_NAME \
  --image $IMAGE_TAG \
  --region $REGION \
  --platform managed \
  --port 8080 \
  --timeout 300 \
  --memory 2Gi \
  --cpu 2 \
  --min-instances 0 \
  --max-instances 10 \
  --allow-unauthenticated \
  --set-env-vars "PORT=8080,WORKERS=4" \
  --set-env-vars "ENV_FILE=$(cat .env)"
```

## 🧪 Post-Deployment Verification

### 1. Check Service Status
```bash
gcloud run services describe $SERVICE_NAME --region $REGION
```

### 2. Test Health Endpoint
```bash
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)')
curl $SERVICE_URL/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "bot-orchestration",
  "port": 8080,
  "workers": 4
}
```

### 3. View Logs
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME" \
  --limit 50 \
  --format json
```

Look for:
- `[STARTUP]` messages showing initialization
- No error messages
- Successful uvicorn startup

### 4. Monitor Metrics
1. Go to Cloud Console → Cloud Run → Your Service
2. Click "Metrics" tab
3. Check:
   - Request count
   - Request latency
   - Container instance count
   - Memory utilization
   - CPU utilization

## 🐛 Troubleshooting

### If Deployment Fails

1. **Check logs immediately**:
   ```bash
   gcloud logging tail "resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME"
   ```

2. **Common Issues**:
   
   **Issue**: Container fails to start
   - Check ENV_FILE is set correctly
   - Verify all required environment variables are present
   - Check startup logs for Python errors

   **Issue**: Timeout during deployment
   - Increase timeout: `--timeout 600`
   - Check if database connections are hanging
   - Verify external API connectivity

   **Issue**: Out of memory
   - Increase memory: `--memory 4Gi`
   - Check for memory leaks in logs

   **Issue**: Health check fails
   - Test locally: `docker run -p 8080:8080 -e ENV_FILE="$(cat .env)" <image>`
   - Check if port 8080 is actually listening
   - Verify uvicorn is starting correctly

### Local Testing Before Deployment

```bash
# Build image
docker build -t bot-test .

# Run with same settings as Cloud Run
docker run -p 8080:8080 \
  -e PORT=8080 \
  -e WORKERS=4 \
  -e ENV_FILE="$(cat .env)" \
  bot-test

# In another terminal, test
curl http://localhost:8080/health
```

## 📊 Resource Recommendations

### Development/Staging
```bash
--memory 2Gi
--cpu 2
--min-instances 0
--max-instances 5
--timeout 300
```

### Production
```bash
--memory 4Gi
--cpu 4
--min-instances 1  # Keep at least 1 instance warm
--max-instances 20
--timeout 300
--concurrency 80   # Requests per container
```

## 🔒 Security Best Practices

1. **Use Secret Manager** for sensitive data:
   ```bash
   # Store secret
   echo -n "your-api-key" | gcloud secrets create openai-api-key --data-file=-
   
   # Grant access
   gcloud secrets add-iam-policy-binding openai-api-key \
     --member="serviceAccount:$PROJECT_ID-compute@developer.gserviceaccount.com" \
     --role="roles/secretmanager.secretAccessor"
   
   # Use in Cloud Run
   gcloud run services update $SERVICE_NAME \
     --update-secrets AGENT_CONFIG__API_KEY=openai-api-key:latest
   ```

2. **Use IAM for authentication** (instead of `--allow-unauthenticated`):
   ```bash
   gcloud run services update $SERVICE_NAME \
     --no-allow-unauthenticated
   ```

3. **Enable VPC connector** for private resources:
   ```bash
   gcloud run services update $SERVICE_NAME \
     --vpc-connector your-connector \
     --vpc-egress all-traffic
   ```

## 📝 Summary of Changes

### Files Modified
1. `Dockerfile` - Better entrypoint with logging
2. `src/bot/app.py` - Health endpoint + startup logging
3. `src/bot/config.py` - Default auth values
4. `.github/workflows/deploy-cloud-run.yml` - Proper Cloud Run flags

### Files Created
1. `CLOUD_RUN_FIX.md` - Detailed fix documentation
2. `deploy-to-cloud-run.sh` - Manual deployment script
3. `DEPLOYMENT_CHECKLIST.md` - This checklist

### Action Required
⚠️ **Add `CLOUD_RUN_ENV_FILE` secret to GitHub** before pushing!

## 🎯 Next Steps

1. [ ] Add GitHub secret `CLOUD_RUN_ENV_FILE`
2. [ ] Commit and push changes
3. [ ] Monitor GitHub Actions deployment
4. [ ] Test health endpoint
5. [ ] Check application logs
6. [ ] Verify service functionality
7. [ ] (Optional) Set up Secret Manager for production
8. [ ] (Optional) Configure custom domain
9. [ ] (Optional) Set up Cloud Monitoring alerts
