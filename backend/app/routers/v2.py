"""
V2 API Router - Phased generation with HITL gates.

All endpoints under /api/v2/ -- existing /api/ endpoints are untouched.
"""
import logging
import shutil
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, UploadFile, HTTPException

from ..models.phase_models import (
    CreateSessionRequest,
    CreateSessionResponse,
    SubmitQuestionnaireRequest,
    SubmitQuestionnaireResponse,
    UploadResponse,
    StartPhaseResponse,
    PhaseProgressResponse,
    PhaseReviewResponse,
    ApprovePhaseRequest,
    ApprovePhaseResponse,
    RejectPhaseRequest,
    RejectPhaseResponse,
    SessionListResponse,
)
from ..store.phase_store import PhaseStore
from ..services.phase_service import PhaseService

logger = logging.getLogger(__name__)

# Router prefix
router = APIRouter(prefix="/api/v2", tags=["v2-phased"])

# These will be initialized by the app startup
_phase_service: Optional[PhaseService] = None


def init_phase_service(base_output_dir: Path, base_temp_dir: Path, db_path: Path):
    """Initialize the phase service. Called from main.py on startup."""
    global _phase_service
    store = PhaseStore(db_path)
    _phase_service = PhaseService(store, base_output_dir, base_temp_dir)
    logger.info(f"PhaseService initialized: db={db_path}")


def get_phase_service() -> PhaseService:
    if _phase_service is None:
        raise HTTPException(status_code=503, detail="Phase service not initialized")
    return _phase_service


@router.post("/sessions", response_model=CreateSessionResponse)
async def create_session(request: CreateSessionRequest):
    """Create a new phased generation session."""
    svc = get_phase_service()
    if request.flow_type not in ("greenfield", "modernization"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid flow_type: {request.flow_type}. Must be 'greenfield' or 'modernization'."
        )
    try:
        result = svc.create_session(request.flow_type)
        return result
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/questionnaire")
async def get_questionnaire(session_id: str):
    """Get questionnaire schema and any saved answers for a session."""
    svc = get_phase_service()
    session = svc.store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    flow_type = session["flow_type"]
    try:
        import sys
        from pathlib import Path as P
        sys.path.insert(0, str(P(__file__).parent.parent.parent.parent))
        from prdgen.intake.questionnaire import get_questions
        questions = get_questions(flow_type)
        saved = svc.store.get_questionnaire(session_id)
        saved_answers = saved.get("answers", {})
        required = [q for q in questions if q.get("required")]
        answered = [q for q in required if (saved_answers.get(q["id"], "")).strip()]
        return {
            "flow_type": flow_type,
            "questions": questions,
            "saved_answers": saved_answers,
            "completion": {
                "total": len(required),
                "answered": len(answered),
                "pct": round(len(answered) / len(required) * 100) if required else 100,
            },
        }
    except Exception as e:
        logger.error(f"Error getting questionnaire: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/questionnaire", response_model=SubmitQuestionnaireResponse)
async def submit_questionnaire(session_id: str, request: SubmitQuestionnaireRequest):
    """Submit questionnaire answers for a session."""
    svc = get_phase_service()
    try:
        result = svc.submit_questionnaire(session_id, request.answers)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error submitting questionnaire: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/upload", response_model=UploadResponse)
async def upload_documents(session_id: str, files: list[UploadFile] = File(...)):
    """Upload documents for a session."""
    svc = get_phase_service()
    try:
        file_data = []
        for f in files:
            if f.filename:
                content = await f.read()
                file_data.append({
                    "filename": f.filename,
                    "content": content,
                })
        result = svc.upload_documents(session_id, file_data)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error uploading documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/phases/{phase_number}/generate", response_model=StartPhaseResponse)
async def start_phase_generation(session_id: str, phase_number: int):
    """Start generation for a phase. Returns immediately; generation runs in background."""
    svc = get_phase_service()
    if phase_number not in (1, 2, 3):
        raise HTTPException(status_code=400, detail="Phase number must be 1, 2, or 3.")
    try:
        result = svc.start_phase(session_id, phase_number)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error starting phase: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/phases/{phase_number}/status", response_model=PhaseProgressResponse)
async def get_phase_status(session_id: str, phase_number: int):
    """Get real-time progress of phase generation."""
    svc = get_phase_service()
    try:
        result = svc.get_phase_progress(session_id, phase_number)
        return result
    except Exception as e:
        logger.error(f"Error getting phase status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/phases/{phase_number}/review", response_model=PhaseReviewResponse)
async def get_phase_review(session_id: str, phase_number: int):
    """Get artifacts for review with edit permissions."""
    svc = get_phase_service()
    try:
        result = svc.get_phase_review(session_id, phase_number)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting phase review: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/phases/{phase_number}/approve", response_model=ApprovePhaseResponse)
async def approve_phase(session_id: str, phase_number: int, request: ApprovePhaseRequest):
    """Approve a phase with optional edited artifacts."""
    svc = get_phase_service()
    try:
        result = svc.approve_phase(
            session_id, phase_number,
            approved_by=request.approved_by,
            notes=request.notes,
            edited_artifacts=request.edited_artifacts,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error approving phase: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/phases/{phase_number}/reject", response_model=RejectPhaseResponse)
async def reject_phase(session_id: str, phase_number: int, request: RejectPhaseRequest):
    """Reject a phase with feedback for re-generation."""
    svc = get_phase_service()
    try:
        result = svc.reject_phase(session_id, phase_number, request.feedback)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error rejecting phase: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/snapshots")
async def get_session_snapshots(session_id: str):
    """Get all phase snapshots for a session."""
    svc = get_phase_service()
    try:
        gates = svc.store.get_all_phase_gates(session_id)
        phases = []
        for gate in gates:
            artifacts = svc.store.get_phase_artifacts(session_id, gate["phase_number"])
            phases.append({
                "number": gate["phase_number"],
                "name": gate["phase_name"],
                "status": gate["status"],
                "artifacts": [
                    {
                        "type": a["artifact_type"],
                        "hash": a["content_hash"],
                        "was_edited": a.get("was_edited", False),
                        "chars": a.get("char_count", 0),
                    }
                    for a in artifacts
                ],
            })
        return {"session_id": session_id, "phases": phases}
    except Exception as e:
        logger.error(f"Error getting snapshots: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/snapshots/{phase_number}/download")
async def download_phase_snapshot(session_id: str, phase_number: int):
    """Download a phase snapshot as a ZIP file."""
    from fastapi.responses import FileResponse

    svc = get_phase_service()
    gate = svc.store.get_phase_gate(session_id, phase_number)
    if not gate or not gate.get("snapshot_dir"):
        raise HTTPException(status_code=404, detail="Snapshot not found.")

    snapshot_dir = Path(gate["snapshot_dir"])
    if not snapshot_dir.exists():
        raise HTTPException(status_code=404, detail="Snapshot directory not found.")

    # Create ZIP
    zip_base = snapshot_dir.parent / f"phase_{phase_number}_snapshot"
    zip_path = shutil.make_archive(str(zip_base), 'zip', snapshot_dir)

    return FileResponse(
        path=zip_path,
        media_type="application/zip",
        filename=f"phase_{phase_number}_snapshot.zip"
    )


@router.get("/sessions/{session_id}/export")
async def export_assessment_pack(session_id: str):
    """Download a consolidated Assessment Pack ZIP containing all approved phase artifacts."""
    from fastapi.responses import FileResponse
    import tempfile
    import json

    svc = get_phase_service()
    session = svc.store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    # Verify all 3 phases are approved
    gates = svc.store.get_all_phase_gates(session_id)
    gate_map = {g["phase_number"]: g for g in gates}
    for pn in (1, 2, 3):
        gate = gate_map.get(pn)
        if not gate or gate["status"] != "approved":
            raise HTTPException(
                status_code=400,
                detail=f"Phase {pn} is not approved. All 3 phases must be approved to export."
            )

    # Build export directory structure
    export_dir = Path(tempfile.mkdtemp(prefix=f"export_{session_id[:8]}_"))
    phase_names = {1: "Phase1_Foundation", 2: "Phase2_Planning", 3: "Phase3_Detail"}

    for pn in (1, 2, 3):
        phase_dir = export_dir / phase_names[pn]
        phase_dir.mkdir()

        artifacts = svc.store.get_phase_artifacts(session_id, pn)
        for art in artifacts:
            src = Path(art["file_path"])
            if src.exists():
                dest = phase_dir / src.name
                shutil.copy2(str(src), str(dest))

    # Generate change log from audit log
    audit_entries = svc.store.get_audit_log(session_id, limit=500)
    if audit_entries:
        changelog_lines = [
            f"# Assessment Change Log",
            f"",
            f"Session: {session_id}",
            f"Flow Type: {session['flow_type']}",
            f"Exported: {_now_iso()}",
            f"",
            f"---",
            f"",
        ]
        for entry in reversed(audit_entries):
            detail_str = ""
            if entry.get("detail"):
                try:
                    detail = json.loads(entry["detail"]) if isinstance(entry["detail"], str) else entry["detail"]
                    detail_str = f" — {json.dumps(detail)}"
                except (json.JSONDecodeError, TypeError):
                    detail_str = f" — {entry['detail']}"
            phase_str = f" [Phase {entry['phase_number']}]" if entry.get("phase_number") else ""
            changelog_lines.append(
                f"- **{entry['created_at']}** | {entry['event_type']}{phase_str} | {entry.get('actor', 'system')}{detail_str}"
            )
        changelog_path = export_dir / "CHANGELOG.md"
        changelog_path.write_text("\n".join(changelog_lines), encoding="utf-8")

    # Create ZIP
    zip_base = export_dir.parent / f"assessment_pack_{session_id[:12]}"
    zip_path = shutil.make_archive(str(zip_base), 'zip', export_dir)

    return FileResponse(
        path=zip_path,
        media_type="application/zip",
        filename=f"assessment_pack_{session_id[:12]}.zip"
    )


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(status: Optional[str] = None, limit: int = 50):
    """List all phased generation sessions."""
    svc = get_phase_service()
    sessions = svc.list_sessions(status=status, limit=limit)
    return {"sessions": sessions, "total": len(sessions)}


@router.get("/sessions/{session_id}")
async def get_session_detail(session_id: str):
    """Get full session details including all phases and audit log."""
    svc = get_phase_service()
    summary = svc.get_session_summary(session_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Session not found.")
    return summary
