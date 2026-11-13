#!/bin/bash
set -e

# Configuration
PROJECT_ID=$(gcloud config get-value project)
REGION="${GCP_REGION:-us-central1}"
JOB_NAME="breachblog-daily-publisher"
TRIGGER_NAME="breachblog-daily-trigger"
SCHEDULE="0 9 * * *" # 09:00 UTC daily (1:00 AM PST)

if [ -z "$PROJECT_ID" ]; then
    echo "Error: No active GCP project configured. Run 'gcloud config set project <PROJECT_ID>'."
    exit 1
fi

echo "=== Setting up BreachBlog Daily Cron on Google Cloud ==="
echo "Project ID: $PROJECT_ID"
echo "Region:     $REGION"
echo "Schedule:   $SCHEDULE"

# 1. Enable required GCP services
echo "--> Enabling required APIs..."
gcloud services enable \
    run.googleapis.com \
    cloudscheduler.googleapis.com \
    cloudbuild.googleapis.com \
    artifactregistry.googleapis.com \
    secretmanager.googleapis.com

# 2. Create Artifact Registry repository if it doesn't exist
REPO_NAME="breachblog"
if ! gcloud artifacts repositories describe "$REPO_NAME" --location="$REGION" &>/dev/null; then
    echo "--> Creating Artifact Registry repository '$REPO_NAME'..."
    gcloud artifacts repositories create "$REPO_NAME" \
        --repository-format=docker \
        --location="$REGION" \
        --description="Docker repository for breachblog daily publisher"
fi

IMAGE_URI="$REGION-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/publisher:latest"

# 3. Build container using Cloud Build
echo "--> Building container image with Google Cloud Build..."
gcloud builds submit --tag "$IMAGE_URI" .

# 4. Create or update Cloud Run Job
echo "--> Configuring Google Cloud Run Job..."
if gcloud run jobs describe "$JOB_NAME" --region="$REGION" &>/dev/null; then
    gcloud run jobs update "$JOB_NAME" \
        --image="$IMAGE_URI" \
        --region="$REGION" \
        --tasks=1 \
        --max-retries=2 \
        --task-timeout=30m
else
    gcloud run jobs create "$JOB_NAME" \
        --image="$IMAGE_URI" \
        --region="$REGION" \
        --tasks=1 \
        --max-retries=2 \
        --task-timeout=30m
fi

# 5. Service account for Cloud Scheduler invocation
SA_NAME="breachblog-invoker"
SA_EMAIL="$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com"
if ! gcloud iam service-accounts describe "$SA_EMAIL" &>/dev/null; then
    echo "--> Creating Service Account for Cloud Scheduler..."
    gcloud iam service-accounts create "$SA_NAME" \
        --display-name="BreachBlog Daily Job Scheduler Invoker"
fi

# Grant invoker role
gcloud run jobs add-iam-policy-binding "$JOB_NAME" \
    --region="$REGION" \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/run.invoker"

# 6. Configure Cloud Scheduler Job
echo "--> Configuring Google Cloud Scheduler Job..."
JOB_EXEC_URL="https://$REGION-run.googleapis.com/v2/projects/$PROJECT_ID/locations/$REGION/jobs/$JOB_NAME:run"

if gcloud scheduler jobs describe "$TRIGGER_NAME" --location="$REGION" &>/dev/null; then
    gcloud scheduler jobs update http "$TRIGGER_NAME" \
        --location="$REGION" \
        --schedule="$SCHEDULE" \
        --uri="$JOB_EXEC_URL" \
        --http-method=POST \
        --oauth-service-account-email="$SA_EMAIL" \
        --time-zone="UTC"
else
    gcloud scheduler jobs create http "$TRIGGER_NAME" \
        --location="$REGION" \
        --schedule="$SCHEDULE" \
        --uri="$JOB_EXEC_URL" \
        --http-method=POST \
        --oauth-service-account-email="$SA_EMAIL" \
        --time-zone="UTC"
fi

echo "=== Google Cloud Cron Setup Complete ==="
