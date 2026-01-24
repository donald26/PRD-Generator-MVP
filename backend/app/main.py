"""
FastAPI application for PRD Generator
Provides REST API endpoints for generating PRD artifacts
"""
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path
import shutil
import uuid
import logging
import threading

from .services.prd_service import generate_artifacts

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="PRD Generator API",
    description="Generate PRD, Epics, Features, and User Stories from documents",
    version="1.0.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directories
BASE_DIR = Path(__file__).parent.parent
TEMP_DIR = BASE_DIR / "temp"
OUTPUT_DIR = BASE_DIR / "outputs"
TEMP_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# In-memory progress tracking
job_progress = {}

def update_job_progress(job_id: str, step: str, progress: int, message: str):
    """Update progress for a job"""
    job_progress[job_id] = {
        "step": step,
        "progress": progress,
        "message": message,
        "status": "processing"
    }
    logger.info(f"Job {job_id}: {step} ({progress}%) - {message}")

def run_generation_background(job_id: str, job_temp_dir: Path, job_output_dir: Path,
                              model_id: str, max_new_tokens: int, temperature: float):
    """Run artifact generation in background thread"""
    try:
        logger.info(f"Background generation started for job {job_id}")

        # Generate artifacts
        generate_artifacts(
            input_dir=str(job_temp_dir),
            output_dir=str(job_output_dir),
            model_id=model_id,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            progress_callback=lambda step, progress, message: update_job_progress(job_id, step, progress, message)
        )

        # Create ZIP file
        logger.info(f"Creating ZIP file for job {job_id}")
        update_job_progress(job_id, "Creating ZIP", 95, "Creating download package...")
        zip_path = OUTPUT_DIR / f"{job_id}"
        shutil.make_archive(str(zip_path), 'zip', job_output_dir)

        # Cleanup temp directory
        if job_temp_dir.exists():
            shutil.rmtree(job_temp_dir)
        logger.info(f"Cleaned up temp directory for job {job_id}")

        # Clean up progress tracking
        if job_id in job_progress:
            del job_progress[job_id]

        logger.info(f"Background generation completed for job {job_id}")

    except Exception as e:
        logger.error(f"Error in background job {job_id}: {str(e)}")
        job_progress[job_id] = {
            "step": "Error",
            "progress": 0,
            "message": str(e),
            "status": "failed"
        }
        # Cleanup on error
        if job_temp_dir.exists():
            shutil.rmtree(job_temp_dir)
        if job_output_dir.exists():
            shutil.rmtree(job_output_dir)

# Request models
class GenerateFromPathRequest(BaseModel):
    folder_path: str
    model_id: str = "Qwen/Qwen2.5-1.5B-Instruct"
    max_new_tokens: int = 800
    temperature: float = 0.5

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "message": "PRD Generator API is running",
        "version": "1.0.0"
    }

@app.post("/api/generate")
async def generate_from_upload(
    files: list[UploadFile] = File(...),
    model_id: str = "Qwen/Qwen2.5-1.5B-Instruct",
    max_new_tokens: int = 800,
    temperature: float = 0.5
):
    """
    Upload documents and generate all PRD artifacts
    Returns immediately with job_id, generation runs in background

    Returns:
    - job_id: Unique identifier for this generation
    - status: Job status (will be 'processing')
    - message: Status message
    """
    job_id = str(uuid.uuid4())
    job_temp_dir = TEMP_DIR / job_id
    job_output_dir = OUTPUT_DIR / job_id

    try:
        logger.info(f"Starting generation job {job_id} with {len(files)} files")

        # Create directories
        job_temp_dir.mkdir(exist_ok=True)
        job_output_dir.mkdir(exist_ok=True)

        # Save uploaded files
        for file in files:
            if not file.filename:
                continue
            file_path = job_temp_dir / file.filename
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)
            logger.info(f"Saved file: {file.filename}")

        # Initialize progress
        update_job_progress(job_id, "Starting", 0, "Initializing generation...")

        # Start generation in background thread
        thread = threading.Thread(
            target=run_generation_background,
            args=(job_id, job_temp_dir, job_output_dir, model_id, max_new_tokens, temperature),
            daemon=True
        )
        thread.start()

        # Return immediately
        return {
            "job_id": job_id,
            "status": "processing",
            "message": "Generation started. Use /api/jobs/{job_id}/progress to check status.",
            "progress_url": f"/api/jobs/{job_id}/progress"
        }

    except Exception as e:
        logger.error(f"Error starting job {job_id}: {str(e)}")
        # Cleanup on error
        if job_temp_dir.exists():
            shutil.rmtree(job_temp_dir)
        if job_output_dir.exists():
            shutil.rmtree(job_output_dir)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate-from-path")
async def generate_from_path(request: GenerateFromPathRequest):
    """
    Generate artifacts from an existing folder path on the server

    Returns:
    - job_id: Unique identifier for this generation
    - output_path: Path where artifacts were generated
    - status: Generation status
    """
    job_id = str(uuid.uuid4())
    job_output_dir = OUTPUT_DIR / job_id

    try:
        # Validate folder path exists
        folder_path = Path(request.folder_path)
        if not folder_path.exists():
            raise HTTPException(status_code=400, detail=f"Folder not found: {request.folder_path}")

        if not folder_path.is_dir():
            raise HTTPException(status_code=400, detail=f"Path is not a directory: {request.folder_path}")

        logger.info(f"Starting generation job {job_id} from path: {request.folder_path}")

        # Initialize progress
        update_job_progress(job_id, "Starting", 0, "Initializing generation...")

        # Create output directory
        job_output_dir.mkdir(exist_ok=True)

        # Generate artifacts
        generate_artifacts(
            input_dir=str(folder_path),
            output_dir=str(job_output_dir),
            model_id=request.model_id,
            max_new_tokens=request.max_new_tokens,
            temperature=request.temperature,
            progress_callback=lambda step, progress, message: update_job_progress(job_id, step, progress, message)
        )

        logger.info(f"Generation complete for job {job_id}")

        # Clean up progress tracking
        if job_id in job_progress:
            del job_progress[job_id]

        return {
            "job_id": job_id,
            "output_path": str(job_output_dir),
            "status": "completed",
            "message": f"Artifacts generated successfully in {job_output_dir}"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in job {job_id}: {str(e)}")
        if job_output_dir.exists():
            shutil.rmtree(job_output_dir)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/download/{job_id}")
async def download_artifacts(job_id: str):
    """
    Download generated artifacts as a ZIP file
    """
    zip_path = OUTPUT_DIR / f"{job_id}.zip"

    if not zip_path.exists():
        raise HTTPException(status_code=404, detail="Artifacts not found. Job may not exist or has expired.")

    return FileResponse(
        path=zip_path,
        media_type="application/zip",
        filename=f"prd-artifacts-{job_id}.zip"
    )

@app.get("/api/jobs/{job_id}/progress")
async def get_job_progress(job_id: str):
    """
    Get real-time progress of a generation job
    """
    # Check if job is in progress
    if job_id in job_progress:
        return job_progress[job_id]

    # Check if job is completed
    zip_path = OUTPUT_DIR / f"{job_id}.zip"
    output_dir = OUTPUT_DIR / job_id

    if zip_path.exists():
        return {
            "step": "Complete",
            "progress": 100,
            "message": "All artifacts generated successfully",
            "status": "completed",
            "download_url": f"/api/download/{job_id}"
        }
    elif output_dir.exists():
        return {
            "step": "Complete",
            "progress": 100,
            "message": "Artifacts generated successfully",
            "status": "completed",
            "output_path": str(output_dir)
        }
    else:
        raise HTTPException(status_code=404, detail="Job not found")

@app.get("/api/jobs/{job_id}")
async def get_job_status(job_id: str):
    """
    Get status of a generation job
    """
    output_dir = OUTPUT_DIR / job_id
    zip_path = OUTPUT_DIR / f"{job_id}.zip"

    if zip_path.exists():
        return {
            "job_id": job_id,
            "status": "completed",
            "output_path": str(output_dir) if output_dir.exists() else None,
            "download_url": f"/api/download/{job_id}"
        }
    elif output_dir.exists():
        return {
            "job_id": job_id,
            "status": "processing",
            "output_path": str(output_dir)
        }
    else:
        raise HTTPException(status_code=404, detail="Job not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
