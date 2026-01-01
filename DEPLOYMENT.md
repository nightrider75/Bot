# Deployment Guide - Google Cloud Run

This guide will help you set up CI/CD for deploying your bot service to Google Cloud Run using GitHub Actions.

## Prerequisites

1. **Google Cloud Project** with billing enabled
2. **GitHub Repository** with Actions enabled
3. **GCP Service Account** with necessary permissions
4. **Artifact Registry** repository for Docker images
5. **Cloud Run** service (will be created automatically on first deploy)

## Step 1: Set Up Google Cloud Resources

### 1.1 Create Artifact Registry Repository

```bash
# Set your variables
export PROJECT_ID="your-gcp-project-id"
export REGION="us-central1"  # or your preferred region
export REPOSITORY="your-repo-name"  # e.g., "bot-images"
export SERVICE_NAME="bot-service"  # Cloud Run service name

# Create Artifact Registry repository
gcloud artifacts repositories create $REPOSITORY \
    --repository-format=docker \
    --location=$REGION \
    --project=$PROJECT_ID
```

### 1.2 Create Service Account

```bash
# Create service account
gcloud iam service-accounts create github-actions-sa \
    --display-name="GitHub Actions Service Account" \
    --project=$PROJECT_ID

# Grant necessary permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:github-actions-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:github-actions-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:github-actions-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/iam.serviceAccountUser"
```

### 1.3 Create and Download Service Account Key

```bash
# Create key
gcloud iam service-accounts keys create github-actions-key.json \
    --iam-account=github-actions-sa@$PROJECT_ID.iam.gserviceaccount.com \
    --project=$PROJECT_ID

# The key will be saved as github-actions-key.json
# You'll need to add this to GitHub Secrets (see Step 2)
```

## Step 2: Configure GitHub Secrets

Go to your GitHub repository → Settings → Secrets and variables → Actions, and add the following secrets:

1. **GCP_PROJECT_ID**: Your Google Cloud Project ID
   - Example: `my-bot-project-123456`

2. **GCP_SERVICE_NAME**: Name of your Cloud Run service
   - Example: `bot-service`

3. **GCP_REGION**: GCP region where resources are located
   - Example: `us-central1`

4. **GCP_ARTIFACT_REGISTRY_REPO**: Name of your Artifact Registry repository
   - Example: `bot-images`

5. **GCP_SA_KEY**: The entire contents of the `github-actions-key.json` file
   - Copy the entire JSON content from the file created in Step 1.3

## Step 3: Environment Variables for Cloud Run

Your application uses environment variables for configuration. The container automatically creates a `.env` file from the `ENV_FILE` environment variable.

### Setting ENV_FILE in Cloud Run

The `ENV_FILE` environment variable should contain the entire contents of your `.env` file as a single string (with newlines preserved).

**Option A: Set via Cloud Console (Recommended)**

1. Go to Cloud Run → Your Service → Edit & Deploy New Revision
2. Add environment variable `ENV_FILE` under "Variables & Secrets"
3. Paste the entire contents of your `.env` file as the value
   - Make sure to preserve newlines and formatting
   - Example: `DATABASE_URL=postgresql://...\nAPI_KEY=your-key\nPORT=8080`

**Option B: Add to GitHub Actions Workflow**

You can add the `ENV_FILE` environment variable directly in the workflow file (`.github/workflows/deploy-cloud-run.yml`) in the deploy step:

```yaml
--set-env-vars PORT=8080,ENV_FILE="${{ secrets.ENV_FILE }}"
```

Then add `ENV_FILE` as a GitHub secret containing your entire `.env` file contents.

**Option C: Use Secret Manager (Most Secure)**

For sensitive data, use Google Secret Manager:

1. Store your `.env` file content in Secret Manager:
   ```bash
   echo -n "$(cat .env)" | gcloud secrets create env-file --data-file=-
   ```

2. Reference it in Cloud Run:
   ```bash
   gcloud run services update $SERVICE_NAME \
     --update-secrets=ENV_FILE=env-file:latest \
     --region $REGION
   ```

**Note**: The entrypoint script will automatically create `/app/.env` from the `ENV_FILE` environment variable when the container starts.

## Step 5: Test the Deployment

1. Push to the `main` branch or merge a PR
2. GitHub Actions will automatically:
   - Build the Docker image
   - Push to Artifact Registry
   - Deploy to Cloud Run

3. Check the deployment:
   ```bash
   gcloud run services describe $SERVICE_NAME \
     --region $REGION \
     --project $PROJECT_ID
   ```

## Step 6: Customize Cloud Run Settings

You can modify the Cloud Run deployment settings in `.github/workflows/deploy-cloud-run.yml`:

- **Memory**: Currently set to `2Gi` (adjust based on your needs)
- **CPU**: Currently set to `2` (adjust based on your needs)
- **Timeout**: Currently set to `300` seconds (5 minutes)
- **Max Instances**: Currently set to `10` (adjust based on traffic)
- **Min Instances**: Add `--min-instances 1` if you want to keep at least one instance warm

## Troubleshooting

### Build Fails
- Check that git submodules are properly initialized
- Verify Poetry dependencies are correct
- Check Docker build logs in GitHub Actions

### Deployment Fails
- Verify service account has correct permissions
- Check that Artifact Registry repository exists
- Verify all secrets are set correctly in GitHub

### Application Errors
- Check Cloud Run logs: `gcloud run services logs read $SERVICE_NAME --region $REGION`
- Verify `ENV_FILE` environment variable is set correctly and contains valid `.env` content
- Verify PORT environment variable is set to 8080
- Check that the `.env` file was created: Look for "Created .env file from ENV_FILE environment variable" in logs

## Security Best Practices

1. **Use Secret Manager**: Store your `ENV_FILE` content in Google Secret Manager instead of plain environment variables
2. **Least Privilege**: Service account should only have necessary permissions
3. **Private Images**: Consider making Artifact Registry repository private
4. **IAM**: Restrict who can access the Cloud Run service
5. **Encryption**: Ensure secrets are encrypted at rest in Secret Manager

## Cost Optimization

- Set appropriate min/max instances based on traffic
- Use Cloud Run's automatic scaling (0 to N instances)
- Monitor usage in GCP Console

## Next Steps

1. Set up monitoring and alerting in Cloud Run
2. Configure custom domain (if needed)
3. Set up Cloud CDN for static assets (if applicable)
4. Configure Cloud Armor for DDoS protection (if needed)

