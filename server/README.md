# ChallanAI — Server Deployment (GCP Cloud Run)

## Quick Deploy

```bash
# Authenticate
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Enable required APIs
gcloud services enable cloudbuild.googleapis.com run.googleapis.com

# Deploy (from repo root)
gcloud builds submit --config server/cloudbuild.yaml .

# Or build & deploy manually
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/challanai .
gcloud run deploy challanai \
  --image gcr.io/YOUR_PROJECT_ID/challanai \
  --region asia-south1 \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi
```

## Local Development

```bash
cd server
pip install -r requirements.txt
uvicorn api:app --reload --port 8000
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/generate` | Excel → Excel invoice |
| `POST` | `/generate-pdf` | Excel → PDF invoice |
| `POST` | `/generate-from-image` | Image → Excel invoice |
| `POST` | `/generate-from-image-pdf` | Image → PDF invoice |
| `POST` | `/batch` | Zip of Excel files → Zip of invoices |

All `POST` endpoints accept `file` (upload) and optional `inv_num` / `start_num` form fields.
