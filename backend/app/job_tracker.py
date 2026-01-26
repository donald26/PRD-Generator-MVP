"""
Simple JSON-based job tracking system
Persists job information across server restarts
"""
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from threading import Lock

logger = logging.getLogger(__name__)

class JobTracker:
    """Tracks job status using JSON file storage"""

    def __init__(self, storage_path: Path):
        self.storage_path = storage_path
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = Lock()
        self._load_jobs()

    def _load_jobs(self):
        """Load jobs from JSON file"""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r') as f:
                    self.jobs = json.load(f)
                logger.info(f"Loaded {len(self.jobs)} jobs from storage")
            except Exception as e:
                logger.error(f"Error loading jobs: {e}")
                self.jobs = {}
        else:
            self.jobs = {}

    def _save_jobs(self):
        """Save jobs to JSON file"""
        try:
            with self.lock:
                with open(self.storage_path, 'w') as f:
                    json.dump(self.jobs, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving jobs: {e}")

    def create_job(self, job_id: str, artifacts: Optional[List[str]] = None) -> Dict:
        """Create a new job entry"""
        job_data = {
            "job_id": job_id,
            "status": "processing",
            "created_at": datetime.now().isoformat(),
            "artifacts_selected": artifacts or [],
            "progress": 0,
            "current_step": "Starting",
            "message": "Initializing...",
            "output_path": None,
            "download_url": None,
            "error": None
        }

        self.jobs[job_id] = job_data
        self._save_jobs()
        logger.info(f"Created job: {job_id}")
        return job_data

    def update_job(self, job_id: str, **kwargs):
        """Update job fields"""
        if job_id in self.jobs:
            self.jobs[job_id].update(kwargs)
            self.jobs[job_id]["updated_at"] = datetime.now().isoformat()
            self._save_jobs()

    def update_progress(self, job_id: str, step: str, progress: int, message: str):
        """Update job progress"""
        if job_id in self.jobs:
            self.jobs[job_id].update({
                "current_step": step,
                "progress": progress,
                "message": message,
                "updated_at": datetime.now().isoformat()
            })
            self._save_jobs()

    def mark_completed(self, job_id: str, output_path: str, download_url: str):
        """Mark job as completed"""
        if job_id in self.jobs:
            self.jobs[job_id].update({
                "status": "completed",
                "progress": 100,
                "current_step": "Complete",
                "message": "All artifacts generated successfully",
                "output_path": output_path,
                "download_url": download_url,
                "completed_at": datetime.now().isoformat()
            })
            self._save_jobs()
            logger.info(f"Job completed: {job_id}")

    def mark_failed(self, job_id: str, error: str):
        """Mark job as failed"""
        if job_id in self.jobs:
            self.jobs[job_id].update({
                "status": "failed",
                "error": error,
                "failed_at": datetime.now().isoformat()
            })
            self._save_jobs()
            logger.error(f"Job failed: {job_id} - {error}")

    def get_job(self, job_id: str) -> Optional[Dict]:
        """Get job by ID"""
        return self.jobs.get(job_id)

    def list_jobs(self, limit: int = 100) -> List[Dict]:
        """List all jobs, most recent first"""
        jobs_list = list(self.jobs.values())
        # Sort by created_at descending
        jobs_list.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return jobs_list[:limit]

    def delete_job(self, job_id: str):
        """Delete a job entry"""
        if job_id in self.jobs:
            del self.jobs[job_id]
            self._save_jobs()
            logger.info(f"Deleted job: {job_id}")
