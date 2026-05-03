#!/bin/bash
# VoteGuide — Google Cloud Run Deployment Script
# Usage: bash deploy.sh YOUR_PROJECT_ID YOUR_REGION

set -e

PROJECT_ID=${1:-"your-project-id"}
REGION=${2:-"us-central1"}
SERVICE_NAME="voteguide"
IMAGE="gcr.io/$PROJECT_ID/$SERVICE_NAME"

if [ -f .env ]; then
  echo "Loading environment variables from .env..."
  export $(grep -v '^#' .env | xargs)
fi

echo "=== VoteGuide Deployment ==="
echo "Project: $PROJECT_ID"
echo "Region:  $REGION"
echo "Image:   $IMAGE"
echo ""

echo "[1/5] Verifying gcloud configuration..."
gcloud config set project $PROJECT_ID

echo "[2/5] Enabling required Google Cloud APIs..."
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  containerregistry.googleapis.com \
  translate.googleapis.com

echo "[3/5] Building Docker image..."
gcloud builds submit --tag $IMAGE

echo "[4/5] Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image $IMAGE \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --max-instances 10 \
  --set-env-vars \
    GEMINI_API_KEY=$GEMINI_API_KEY,\
    GOOGLE_TRANSLATE_API_KEY=$GOOGLE_TRANSLATE_API_KEY,\
    FIREBASE_PROJECT_ID=$FIREBASE_PROJECT_ID,\
    FIREBASE_WEB_API_KEY=$FIREBASE_WEB_API_KEY

echo "[5/5] Deployment complete!"
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
  --platform managed \
  --region $REGION \
  --format "value(status.url)")
echo ""
echo "=== VoteGuide is live ==="
echo "URL: $SERVICE_URL"
echo "Health check: $SERVICE_URL/health"
echo ""
echo "Update your README.md with this URL:"
echo "$SERVICE_URL"
