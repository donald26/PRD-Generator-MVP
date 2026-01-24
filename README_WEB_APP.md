# PRD Generator Web Application

## Quick Start

### 1. Install Backend Dependencies

```bash
# Make sure you're in the project root
cd /Users/donald.fernandes/Documents/MyDocuments/Repos/PRD-Generator-MVP

# If you haven't already, create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Mac/Linux

# Install existing prdgen dependencies
pip install -r requirements.txt

# Install additional backend dependencies
pip install fastapi uvicorn python-multipart aiofiles
```

### 2. Start the Backend

```bash
cd backend
chmod +x run.sh
./run.sh

# Or manually:
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

### 3. Open the Frontend

```bash
# In a new terminal, open the frontend
open frontend/index.html

# Or serve it with Python:
cd frontend
python3 -m http.server 3000
# Then open http://localhost:3000
```

## Usage

### Option 1: Upload Documents

1. Click "Upload Documents" tab
2. Select files (.txt, .md, .docx)
3. Click "Generate PRD Artifacts"
4. Wait 1-2 minutes
5. Download the ZIP file with all artifacts

### Option 2: Use Folder Path

1. Click "Use Folder Path" tab
2. Enter path to your documents folder (e.g., `examples/loan_underwriting_docs`)
3. Click "Generate PRD Artifacts"
4. Artifacts will be saved in `backend/outputs/[job-id]/`

## API Endpoints

Base URL: `http://localhost:8000`

### POST /api/generate
Upload files and generate artifacts

**Request:** multipart/form-data with files

**Response:**
```json
{
  "job_id": "uuid",
  "download_url": "/api/download/uuid",
  "status": "completed"
}
```

### POST /api/generate-from-path
Generate from existing folder

**Request:**
```json
{
  "folder_path": "/path/to/documents"
}
```

**Response:**
```json
{
  "job_id": "uuid",
  "output_path": "/path/to/outputs/uuid",
  "status": "completed"
}
```

### GET /api/download/{job_id}
Download generated artifacts as ZIP

**Response:** ZIP file

## Troubleshooting

### Backend won't start
```bash
# Check if port 8000 is already in use
lsof -i :8000

# If yes, kill the process or use a different port:
uvicorn app.main:app --port 8001
```

### Import errors
```bash
# Make sure you're in the virtual environment
source .venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
pip install fastapi uvicorn python-multipart aiofiles
```

### Frontend can't connect to backend
- Check that backend is running on http://localhost:8000
- Check browser console for CORS errors
- Make sure API_URL in frontend/index.html matches backend URL

## Project Structure

```
PRD-Generator-MVP/
├── prdgen/                 # Your existing CLI code
├── backend/                # New FastAPI backend
│   ├── app/
│   │   ├── main.py        # FastAPI app
│   │   └── services/
│   │       └── prd_service.py  # Wraps prdgen
│   ├── temp/              # Uploaded files (temporary)
│   └── outputs/           # Generated artifacts
└── frontend/
    └── index.html         # Simple web UI
```

## Next Steps

1. **Test with example data:**
   ```bash
   # In frontend, use folder path:
   examples/loan_underwriting_docs
   ```

2. **Deploy to cloud** (later):
   - Railway.app
   - Render.com
   - AWS/GCP/Azure

3. **Add features** (later):
   - Progress tracking
   - Job history
   - Custom model selection
