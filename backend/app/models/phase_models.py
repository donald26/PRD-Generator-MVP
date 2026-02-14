"""Pydantic models for the v2 phased generation API."""
from pydantic import BaseModel, Field
from typing import Dict, List, Optional


class CreateSessionRequest(BaseModel):
    flow_type: str = Field(..., description="'greenfield' or 'modernization'")


class CreateSessionResponse(BaseModel):
    session_id: str
    flow_type: str
    questionnaire_version: str
    questionnaire: list


class SubmitQuestionnaireRequest(BaseModel):
    answers: Dict[str, str] = Field(..., description="Map of question_id -> answer text")


class SubmitQuestionnaireResponse(BaseModel):
    status: str
    errors: Optional[List[str]] = None
    next_action: Optional[str] = None


class UploadResponse(BaseModel):
    status: str
    file_count: int


class StartPhaseResponse(BaseModel):
    status: str
    phase_number: int
    phase_name: str
    artifacts: List[str]


class PhaseProgressResponse(BaseModel):
    phase_number: Optional[int] = None
    overall_status: str
    overall_progress: int = 0
    artifacts: Dict[str, dict] = {}


class PhaseReviewResponse(BaseModel):
    phase_number: int
    phase_status: str
    flow_type: str
    artifacts: Dict[str, str]
    editable: List[str]


class ApprovePhaseRequest(BaseModel):
    approved_by: str
    notes: str = ""
    edited_artifacts: Optional[Dict[str, str]] = None


class ApprovePhaseResponse(BaseModel):
    status: str
    phase_number: int
    snapshot_dir: Optional[str] = None
    next_phase: Optional[int] = None


class RejectPhaseRequest(BaseModel):
    feedback: str


class RejectPhaseResponse(BaseModel):
    status: str
    can_regenerate: bool
    rejection_count: int


class SessionListResponse(BaseModel):
    sessions: list
    total: int
