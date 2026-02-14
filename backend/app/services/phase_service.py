"""
Phase Service - Orchestrates phased generation with persistence.

Every method coordinates generation logic (via PhasedFlowRunner) with
persistence writes (via PhaseStore), ensuring every state transition
and artifact is durably recorded.
"""
import hashlib
import logging
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Set

LOG = logging.getLogger("backend.services.phase_service")


class PhaseService:
    """Wraps PhasedFlowRunner for the FastAPI backend with full persistence."""

    def __init__(self, phase_store, base_output_dir: Path, base_temp_dir: Path):
        self.store = phase_store
        self.base_output_dir = base_output_dir
        self.base_temp_dir = base_temp_dir

        # Active flow runners keyed by session_id
        self._runners: Dict[str, Any] = {}
        # Lock for thread safety
        self._lock = threading.Lock()

    def create_session(self, flow_type: str) -> dict:
        """Create a new phased generation session."""
        import sys
        from pathlib import Path as P
        sys.path.insert(0, str(P(__file__).parent.parent.parent.parent))
        from prdgen.intake.questionnaire import get_questions, get_questionnaire_version

        session_id = str(uuid.uuid4())

        # Create in DB
        self.store.create_session(session_id, flow_type)
        self.store.log_event(session_id, "session_created", actor="system",
                           detail={"flow_type": flow_type})

        # Load questionnaire
        questions = get_questions(flow_type)
        version = get_questionnaire_version(flow_type)

        self.store.update_session(session_id, questionnaire_ver=version)

        return {
            "session_id": session_id,
            "flow_type": flow_type,
            "questionnaire_version": version,
            "questionnaire": questions,
        }

    def submit_questionnaire(self, session_id: str, answers: dict) -> dict:
        """Submit questionnaire answers for a session."""
        import sys
        from pathlib import Path as P
        sys.path.insert(0, str(P(__file__).parent.parent.parent.parent))
        from prdgen.intake.questionnaire import get_questions, validate_answers

        session = self.store.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        flow_type = session["flow_type"]

        # Validate
        errors = validate_answers(flow_type, answers)
        if errors:
            return {"status": "validation_error", "errors": errors}

        # Store
        questions = get_questions(flow_type)
        self.store.save_questionnaire(session_id, questions, answers)
        self.store.update_session(session_id, status="questionnaire_done")
        self.store.log_event(session_id, "questionnaire_submitted", actor="user",
                           detail={"answer_count": len(answers)})

        return {"status": "ready", "next_action": "upload"}

    def upload_documents(self, session_id: str, files: list) -> dict:
        """Save uploaded files and record in DB."""
        session = self.store.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        input_dir = self.base_temp_dir / session_id
        input_dir.mkdir(parents=True, exist_ok=True)

        saved_files = []
        for file_info in files:
            filename = file_info["filename"]
            content = file_info["content"]

            file_path = input_dir / filename
            file_path.write_bytes(content)

            content_hash = hashlib.sha256(content).hexdigest()
            file_type = file_path.suffix.lstrip(".")

            self.store.save_document(
                session_id, filename, str(file_path),
                len(content), file_type, content_hash
            )
            saved_files.append(filename)

        self.store.update_session(session_id, status="docs_uploaded",
                                input_dir=str(input_dir))
        self.store.log_event(session_id, "docs_uploaded", actor="user",
                           detail={"filenames": saved_files, "count": len(saved_files)})

        return {"status": "uploaded", "file_count": len(saved_files)}

    def start_phase(self, session_id: str, phase_number: int) -> dict:
        """Start generation for a phase. Returns immediately; runs in background."""
        import sys
        from pathlib import Path as P
        sys.path.insert(0, str(P(__file__).parent.parent.parent.parent))
        from prdgen.phased.phases import get_phase_definition
        from prdgen.artifact_types import ARTIFACT_FILENAMES

        session = self.store.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        phase_def = get_phase_definition(phase_number)

        # Check prior phase
        if phase_def.requires_phase is not None:
            prior_gate = self.store.get_phase_gate(session_id, phase_def.requires_phase)
            if not prior_gate or prior_gate["status"] != "approved":
                raise ValueError(
                    f"Phase {phase_number} requires Phase {phase_def.requires_phase} "
                    f"to be approved first."
                )

        # Create phase gate
        gate = self.store.create_phase_gate(session_id, phase_number, phase_def.name)
        gate_id = gate["id"]

        # Init progress rows
        artifact_types = [a.value for a in phase_def.artifacts]
        self.store.init_generation_progress(gate_id, artifact_types)
        self.store.update_session(session_id, status=f"phase_{phase_number}")
        self.store.log_event(session_id, "phase_generation_started",
                           phase_number=phase_number, actor="system")

        # Output directory for this session
        output_dir = self.base_output_dir / session_id
        output_dir.mkdir(parents=True, exist_ok=True)

        # Snapshot base
        snapshot_base = output_dir / "snapshots"
        snapshot_base.mkdir(parents=True, exist_ok=True)

        # Start background generation
        def _background_generate():
            try:
                self._run_phase_generation(
                    session_id, phase_number, gate_id,
                    output_dir, snapshot_base
                )
            except Exception as e:
                LOG.error(f"Phase generation failed for session {session_id}, phase {phase_number}: {e}")
                self.store.update_phase_gate(
                    session_id, phase_number,
                    status="failed"
                )
                self.store.log_event(
                    session_id, "phase_generation_failed",
                    phase_number=phase_number,
                    detail={"error": str(e)}
                )

        thread = threading.Thread(target=_background_generate, daemon=True)
        thread.start()

        return {
            "status": "generating",
            "phase_number": phase_number,
            "phase_name": phase_def.name,
            "artifacts": artifact_types,
        }

    def _run_phase_generation(
        self, session_id: str, phase_number: int,
        gate_id: int, output_dir: Path, snapshot_base: Path
    ):
        """Background phase generation with progress persistence."""
        import sys
        from pathlib import Path as P
        sys.path.insert(0, str(P(__file__).parent.parent.parent.parent))
        from prdgen.phased.phases import get_phase_definition, compute_content_hash
        from prdgen.phased.flows import PhasedFlowRunner
        from prdgen.config import GenerationConfig
        from prdgen.ingest import ingest_folder
        from prdgen.model import load_provider
        from prdgen.artifact_types import ArtifactType, ARTIFACT_FILENAMES

        session = self.store.get_session(session_id)
        flow_type = session["flow_type"]
        phase_def = get_phase_definition(phase_number)

        # Load questionnaire answers from DB
        q_data = self.store.get_questionnaire(session_id)
        answers = q_data.get("answers", {})

        # Ingest documents
        input_dir = session.get("input_dir", "")
        docs = []
        if input_dir and Path(input_dir).exists():
            docs = ingest_folder(
                input_dir,
                include_exts=[".txt", ".md", ".docx"],
                max_files=25,
                max_chars_per_file=12000
            )

        # Create config (provider resolved from env vars or defaults)
        cfg = GenerationConfig(
            save_incremental=True,
            output_dir=output_dir,
            use_cache=True,
            cache_dir=output_dir,
        )

        # Load model provider (local or Gemini, based on PRDGEN_PROVIDER env var)
        loaded = load_provider(cfg)

        # Progress callback that writes to DB
        def progress_cb(artifact: str, status: str, progress: int, message: str):
            try:
                now = datetime.now(timezone.utc).isoformat()
                kwargs = {"status": status, "progress_pct": progress, "message": message}
                if status == "processing" and progress == 0:
                    kwargs["started_at"] = now
                elif status in ("completed", "cached"):
                    kwargs["completed_at"] = now
                self.store.update_artifact_progress(gate_id, artifact, **kwargs)

                # Update overall progress
                total_artifacts = len(phase_def.artifacts)
                progress_list = self.store.get_generation_progress(gate_id)
                completed = sum(1 for p in progress_list if p["status"] in ("completed", "cached"))
                overall = int((completed / total_artifacts) * 100) if total_artifacts > 0 else 0
                self.store.update_phase_gate(session_id, phase_number, overall_progress=overall)

                if status == "completed":
                    self.store.log_event(
                        session_id, "artifact_generated",
                        phase_number=phase_number, artifact_type=artifact,
                        detail={"chars": len(message) if message else 0}
                    )
            except Exception as e:
                LOG.warning(f"Progress callback error: {e}")

        # Create or get runner
        with self._lock:
            runner = self._runners.get(session_id)
            if runner is None:
                runner = PhasedFlowRunner(
                    flow_type=flow_type,
                    questionnaire_answers=answers,
                    cfg=cfg,
                    loaded=loaded,
                    docs=docs,
                    snapshot_base_dir=snapshot_base,
                    progress_callback=progress_cb,
                )
                self._runners[session_id] = runner

        # If phase > 1, load prior snapshots into runner
        if phase_number > 1:
            from prdgen.phased.phases import PhaseStatus
            for pn in range(1, phase_number):
                prior_gate = self.store.get_phase_gate(session_id, pn)
                if prior_gate and prior_gate.get("snapshot_dir"):
                    from prdgen.phased.phases import load_snapshot_from_disk
                    snap = load_snapshot_from_disk(Path(prior_gate["snapshot_dir"]))
                    runner.snapshots[pn] = snap
                    runner.phase_statuses[pn] = (
                        PhaseStatus.APPROVED
                        if prior_gate["status"] == "approved"
                        else PhaseStatus.PENDING
                    )

        # Run the phase
        results = runner.run_phase(phase_number)

        # Persist artifacts
        for artifact_type, content in results.items():
            filename = ARTIFACT_FILENAMES.get(artifact_type, f"{artifact_type.value}.md")
            file_path = output_dir / filename
            file_path.write_text(content, encoding="utf-8")
            content_hash = compute_content_hash(content)

            self.store.save_phase_artifact(
                gate_id, artifact_type.value, content_hash,
                str(file_path), len(content)
            )

        # Mark phase as ready for review
        now = datetime.now(timezone.utc).isoformat()
        self.store.update_phase_gate(
            session_id, phase_number,
            status="review", generated_at=now, overall_progress=100
        )
        self.store.log_event(
            session_id, "phase_review_ready",
            phase_number=phase_number,
            detail={"artifact_count": len(results)}
        )

    def get_phase_progress(self, session_id: str, phase_number: int) -> dict:
        """Get current generation progress for a phase."""
        gate = self.store.get_phase_gate(session_id, phase_number)
        if not gate:
            return {"status": "not_started"}

        progress_items = self.store.get_generation_progress(gate["id"])
        artifacts = {
            p["artifact_type"]: {
                "status": p["status"],
                "progress": p["progress_pct"],
                "message": p.get("message", ""),
            }
            for p in progress_items
        }

        return {
            "phase_number": phase_number,
            "overall_status": gate["status"],
            "overall_progress": gate.get("overall_progress", 0),
            "artifacts": artifacts,
        }

    def get_phase_review(self, session_id: str, phase_number: int) -> dict:
        """Get artifacts for review with edit permissions."""
        gate = self.store.get_phase_gate(session_id, phase_number)
        if not gate or gate["status"] not in ("review", "approved"):
            raise ValueError(f"Phase {phase_number} is not ready for review.")

        session = self.store.get_session(session_id)
        flow_type = session["flow_type"]

        # Load artifact content from disk
        artifact_records = self.store.get_phase_artifacts(session_id, phase_number)
        artifacts = {}
        for rec in artifact_records:
            file_path = Path(rec["file_path"])
            if file_path.exists():
                artifacts[rec["artifact_type"]] = file_path.read_text(encoding="utf-8")

        # Determine editable artifacts
        runner = self._runners.get(session_id)
        editable = []
        if runner:
            editable = runner.get_editable_artifacts(phase_number)
        else:
            # Default: PRD is always editable, capabilities for modernization
            editable = ["prd"]
            if flow_type == "modernization" and phase_number == 1:
                editable.append("capabilities")

        return {
            "phase_number": phase_number,
            "phase_status": gate["status"],
            "flow_type": flow_type,
            "artifacts": artifacts,
            "editable": editable,
        }

    def approve_phase(
        self, session_id: str, phase_number: int,
        approved_by: str, notes: str = "",
        edited_artifacts: Optional[Dict[str, str]] = None,
    ) -> dict:
        """Approve a phase, optionally with HITL-edited artifacts."""
        import sys
        from pathlib import Path as P
        sys.path.insert(0, str(P(__file__).parent.parent.parent.parent))
        from prdgen.phased.phases import compute_content_hash

        gate = self.store.get_phase_gate(session_id, phase_number)
        if not gate or gate["status"] != "review":
            raise ValueError(f"Phase {phase_number} is not in review state.")

        gate_id = gate["id"]
        output_dir = self.base_output_dir / session_id
        snapshot_dir = output_dir / "snapshots" / f"phase_{phase_number}"
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        # Handle edits
        if edited_artifacts:
            originals_dir = snapshot_dir / "originals"
            originals_dir.mkdir(exist_ok=True)

            for artifact_name, edited_content in edited_artifacts.items():
                artifact_records = self.store.get_phase_artifacts(session_id, phase_number)
                for rec in artifact_records:
                    if rec["artifact_type"] == artifact_name:
                        # Read original
                        original_path = Path(rec["file_path"])
                        if original_path.exists():
                            original_content = original_path.read_text(encoding="utf-8")
                            original_hash = compute_content_hash(original_content)
                            edited_hash = compute_content_hash(edited_content)

                            # Backup original
                            backup_path = originals_dir / f"{artifact_name}_original.md"
                            backup_path.write_text(original_content, encoding="utf-8")

                            # Write edited version
                            original_path.write_text(edited_content, encoding="utf-8")

                            # Update DB
                            self.store.update_phase_artifact(
                                gate_id, artifact_name,
                                content_hash=edited_hash, was_edited=True
                            )
                            self.store.save_artifact_edit(
                                rec["id"], original_hash, edited_hash,
                                str(backup_path), approved_by
                            )
                            self.store.log_event(
                                session_id, "artifact_edited",
                                phase_number=phase_number, artifact_type=artifact_name,
                                actor=approved_by,
                                detail={"original_hash": original_hash[:16],
                                        "edited_hash": edited_hash[:16]}
                            )

        # Also approve in the runner if active
        runner = self._runners.get(session_id)
        if runner:
            runner.approve_phase(
                phase_number, approved_by, notes,
                edited_artifacts=edited_artifacts
            )

        # Update DB
        now = datetime.now(timezone.utc).isoformat()
        self.store.update_phase_gate(
            session_id, phase_number,
            status="approved", approved_by=approved_by,
            approval_notes=notes, completed_at=now,
            snapshot_dir=str(snapshot_dir)
        )
        self.store.log_event(
            session_id, "phase_approved",
            phase_number=phase_number, actor=approved_by,
            detail={"notes": notes, "has_edits": bool(edited_artifacts)}
        )

        # Check if all phases complete
        if phase_number == 3:
            self.store.update_session(session_id, status="completed")
            self.store.log_event(session_id, "session_completed", actor="system")

        return {
            "status": "approved",
            "phase_number": phase_number,
            "snapshot_dir": str(snapshot_dir),
            "next_phase": phase_number + 1 if phase_number < 3 else None,
        }

    def reject_phase(self, session_id: str, phase_number: int,
                     feedback: str) -> dict:
        """Reject a phase with feedback."""
        gate = self.store.get_phase_gate(session_id, phase_number)
        if not gate or gate["status"] != "review":
            raise ValueError(f"Phase {phase_number} is not in review state.")

        # Update rejection count
        rejection_count = (gate.get("rejection_count") or 0) + 1
        self.store.update_phase_gate(
            session_id, phase_number,
            status="rejected",
            rejection_feedback=feedback,
            rejection_count=rejection_count
        )
        self.store.log_event(
            session_id, "phase_rejected",
            phase_number=phase_number, actor="user",
            detail={"feedback": feedback, "rejection_count": rejection_count}
        )

        # Also reject in runner
        runner = self._runners.get(session_id)
        if runner:
            runner.reject_phase(phase_number, feedback)

        return {
            "status": "rejected",
            "can_regenerate": True,
            "rejection_count": rejection_count,
        }

    def get_session_summary(self, session_id: str) -> dict:
        """Full session export from DB."""
        return self.store.export_session(session_id)

    def list_sessions(self, status: str = None, limit: int = 50) -> list:
        """List all phased sessions."""
        return self.store.list_sessions(status=status, limit=limit)
