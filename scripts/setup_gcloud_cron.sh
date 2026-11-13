#!/bin/bash
set -e

# Configuration
PROJECT_ID="${GCP_PROJECT:-$(gcloud config get-value project)}"
REGION="${GCP_REGION:-us-central1}"
JOB_NAME="breachblog-daily-publisher"
TRIGGER_NAME="breachblog-daily-trigger"
SCHEDULE="0 9 * * *" # 09:00 UTC daily (1:00 AM PST)
REPO_NAME="breachblog"

if [ -z "$PROJECT_ID" ]; then
    echo "Error: No active GCP project configured. Run 'gcloud config set project <PROJECT_ID>'."
    exit 1
fi

echo "=== Setting up BreachBlog Daily Cron on Google Cloud ==="
echo "Project ID: $PROJECT_ID"
echo "Region:     $REGION"
echo "Schedule:   $SCHEDULE"

# 0. Load local environment variables from .env if present
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$REPO_DIR/.env"

if [ -f "$ENV_FILE" ]; then
    echo "--> Loading environment variables from $ENV_FILE..."
    # Read variables without echoing values
    GEMINI_API_KEY=$(grep -E '^GEMINI_API_KEY=' "$ENV_FILE" | cut -d '=' -f2- | tr -d '"' | tr -d "'")
    GH_TOKEN=$(grep -E '^GH_TOKEN=' "$ENV_FILE" | cut -d '=' -f2- | tr -d '"' | tr -d "'")
fi

if [ -z "$GEMINI_API_KEY" ]; then
    echo "Error: GEMINI_API_KEY is not set in environment or $ENV_FILE"
    exit 1
fi

# 1. Enable required GCP services
echo "--> Enabling required GCP APIs..."
CLOUDSDK_METRICS_REQUEST_ATTRIBUTION="agent-skills/1.0 (skill:gcloud)" gcloud services enable \
    run.googleapis.com \
    cloudscheduler.googleapis.com \
    cloudbuild.googleapis.com \
    artifactregistry.googleapis.com \
    --project="$PROJECT_ID"

# 2. Create Artifact Registry repository if it doesn't exist
if ! gcloud artifacts repositories describe "$REPO_NAME" --location="$REGION" --project="$PROJECT_ID" &>/dev/null; then
    echo "--> Creating Artifact Registry repository '$REPO_NAME' in $REGION..."
    CLOUDSDK_METRICS_REQUEST_ATTRIBUTION="agent-skills/1.0 (skill:gcloud)" gcloud artifacts repositories create "$REPO_NAME" \
        --repository-format=docker \
        --location="$REGION" \
        --description="Docker repository for breachblog daily publisher" \
        --project="$PROJECT_ID"
else
    echo "--> Artifact Registry repository '$REPO_NAME' exists."
fi

IMAGE_URI="$REGION-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/publisher:latest"

# 3. Build container using Cloud Build
echo "--> Building container image with Google Cloud Build..."
CLOUDSDK_METRICS_REQUEST_ATTRIBUTION="agent-skills/1.0 (skill:gcloud)" gcloud builds submit \
    --tag "$IMAGE_URI" \
    --project="$PROJECT_ID" \
    "$REPO_DIR"

# 4. Prepare temporary env-vars-file
TEMP_ENV_YAML=$(mktemp /tmp/breachblog-env-XXXXXX.yaml)
cat <<EOF > "$TEMP_ENV_YAML"
GEMINI_API_KEY: "${GEMINI_API_KEY}"
GH_TOKEN: "${GH_TOKEN}"
EOF
chmod 600 "$TEMP_ENV_YAML"

# 5. Create or update Cloud Run Job
echo "--> Configuring Google Cloud Run Job '$JOB_NAME'..."
if gcloud run jobs describe "$JOB_NAME" --region="$REGION" --project="$PROJECT_ID" &>/dev/null; then
    CLOUDSDK_METRICS_REQUEST_ATTRIBUTION="agent-skills/1.0 (skill:gcloud)" gcloud run jobs update "$JOB_NAME" \
        --image="$IMAGE_URI" \
        --region="$REGION" \
        --tasks=1 \
        --max-retries=2 \
        --task-timeout=30m \
        --env-vars-file="$TEMP_ENV_YAML" \
        --project="$PROJECT_ID"
else
    CLOUDSDK_METRICS_REQUEST_ATTRIBUTION="agent-skills/1.0 (skill:gcloud)" gcloud run jobs create "$JOB_NAME" \
        --image="$IMAGE_URI" \
        --region="$REGION" \
        --tasks=1 \
        --max-retries=2 \
        --task-timeout=30m \
        --env-vars-file="$TEMP_ENV_YAML" \
        --project="$PROJECT_ID"
fi
rm -f "$TEMP_ENV_YAML"

# 6. Service account for Cloud Scheduler invocation
SA_NAME="breachblog-invoker"
SA_EMAIL="$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com"
if ! gcloud iam service-accounts describe "$SA_EMAIL" --project="$PROJECT_ID" &>/dev/null; then
    echo "--> Creating Service Account '$SA_NAME' for Cloud Scheduler..."
    CLOUDSDK_METRICS_REQUEST_ATTRIBUTION="agent-skills/1.0 (skill:gcloud)" gcloud iam service-accounts create "$SA_NAME" \
        --display-name="BreachBlog Daily Job Scheduler Invoker" \
        --project="$PROJECT_ID"
else
    echo "--> Service Account '$SA_NAME' exists."
fi

# Grant invoker role
echo "--> Binding roles/run.invoker to service account..."
CLOUDSDK_METRICS_REQUEST_ATTRIBUTION="agent-skills/1.0 (skill:gcloud)" gcloud run jobs add-iam-policy-binding "$JOB_NAME" \
    --region="$REGION" \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/run.invoker" \
    --project="$PROJECT_ID" >/dev/null

# 7. Configure Cloud Scheduler Job
echo "--> Configuring Google Cloud Scheduler Job '$TRIGGER_NAME'..."
JOB_EXEC_URL="https://$REGION-run.googleapis.com/v2/projects/$PROJECT_ID/locations/$REGION/jobs/$JOB_NAME:run"

if gcloud scheduler jobs describe "$TRIGGER_NAME" --location="$REGION" --project="$PROJECT_ID" &>/dev/null; then
    CLOUDSDK_METRICS_REQUEST_ATTRIBUTION="agent-skills/1.0 (skill:gcloud)" gcloud scheduler jobs update http "$TRIGGER_NAME" \
        --location="$REGION" \
        --schedule="$SCHEDULE" \
        --uri="$JOB_EXEC_URL" \
        --http-method=POST \
        --oauth-service-account-email="$SA_EMAIL" \
        --time-zone="UTC" \
        --project="$PROJECT_ID"
else
    CLOUDSDK_METRICS_REQUEST_ATTRIBUTION="agent-skills/1.0 (skill:gcloud)" gcloud scheduler jobs create http "$TRIGGER_NAME" \
        --location="$REGION" \
        --schedule="$SCHEDULE" \
        --uri="$JOB_EXEC_URL" \
        --http-method=POST \
        --oauth-service-account-email="$SA_EMAIL" \
        --time-zone="UTC" \
        --project="$PROJECT_ID"
fi

echo "========================================================"
echo "=== Google Cloud Cron Setup Complete Successfully! ==="
echo "========================================================"
echo "Cloud Run Job:       $JOB_NAME ($REGION)"
echo "Cloud Scheduler:     $TRIGGER_NAME (Schedule: $SCHEDULE UTC)"
echo "Target Endpoint:     $JOB_EXEC_URL"
echo ""
echo "To test run the job immediately:"
echo "  gcloud run jobs execute $JOB_NAME --region=$REGION --project=$PROJECT_ID --wait"
