from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from typing import Optional, List, Dict, Any
from datetime import datetime


# ── Auth ────────────────────────────────────────────────────────────────────

ALLOWED_DESIGNATIONS = {
    "LEAD FIRE RESCUER (LFR)",
    "FIRE & DISASTER RESCUE (FDR)",
    "OTHER",
}


def normalize_designation(value: str) -> str:
    if value is None:
        return value
    normalized = " ".join(value.strip().upper().split())
    if normalized not in ALLOWED_DESIGNATIONS:
        raise ValueError("Designation must be Lead Fire Rescuer (LFR), Fire & Disaster Rescue (FDR), or Other")
    return normalized

class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: int


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    full_name: str = Field(..., min_length=2)
    father_name: Optional[str] = None
    designation: str
    district: str
    station: Optional[str] = None
    employee_id: Optional[str] = None
    phone: Optional[str] = None

    @field_validator("designation")
    @classmethod
    def validate_designation(cls, value: str) -> str:
        return normalize_designation(value)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6)


# ── User / Profile ───────────────────────────────────────────────────────────

class StaffProfileOut(BaseModel):
    full_name: str
    father_name: Optional[str]
    designation: str
    district: str
    station: Optional[str]
    employee_id: Optional[str]
    phone: Optional[str]

    class Config:
        from_attributes = True


class UserOut(BaseModel):
    id: int
    email: str
    username: str
    role: str
    is_active: bool
    created_at: datetime
    profile: Optional[StaffProfileOut]

    class Config:
        from_attributes = True


# ── Test ─────────────────────────────────────────────────────────────────────

class GenerateQuestionsRequest(BaseModel):
    topic_id: str
    designation: str


class AnswerItem(BaseModel):
    q_index: int
    selected: int   # -1 if unanswered


class SubmitTestRequest(BaseModel):
    topic_id: str
    topic_label: str
    questions: List[Dict[str, Any]]
    answers: List[AnswerItem]
    started_at: str
    time_taken_seconds: Optional[int] = None


class SubtopicScore(BaseModel):
    correct: int
    total: int
    percent: float


class TestAttemptOut(BaseModel):
    id: int
    topic_id: str
    topic_label: str
    total_questions: int
    correct_answers: int
    score_percent: float
    passed: bool
    time_taken_seconds: Optional[int]
    answers: Optional[List[Dict[str, Any]]] = None
    questions: Optional[List[Dict[str, Any]]] = None
    subtopic_scores: Optional[Dict[str, Any]]
    ai_feedback: Optional[str]
    completed_at: datetime
    user: Optional[UserOut]

    class Config:
        from_attributes = True


class TestAttemptSummary(BaseModel):
    id: int
    topic_label: str
    score_percent: float
    passed: bool
    completed_at: datetime

    class Config:
        from_attributes = True


# ── Admin ─────────────────────────────────────────────────────────────────────

class AdminCreateStaffRequest(BaseModel):
    email: EmailStr
    username: str
    password: str
    full_name: str
    father_name: Optional[str] = None
    designation: str
    district: str
    station: Optional[str] = None
    employee_id: Optional[str] = None
    phone: Optional[str] = None

    @field_validator("designation")
    @classmethod
    def validate_designation(cls, value: str) -> str:
        return normalize_designation(value)


class AdminUpdateStaffRequest(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(default=None, min_length=3, max_length=50)
    password: Optional[str] = Field(default=None, min_length=6)
    full_name: Optional[str] = Field(default=None, min_length=2)
    father_name: Optional[str] = None
    designation: Optional[str] = None
    district: Optional[str] = None
    station: Optional[str] = None
    employee_id: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("designation")
    @classmethod
    def validate_designation(cls, value: Optional[str]) -> Optional[str]:
        return normalize_designation(value)


class MasterPaperGenerateRequest(BaseModel):
    title: str = Field(default="Master Test Paper", min_length=3, max_length=120)
    easy_count: int = Field(default=10, ge=0, le=100)
    medium_count: int = Field(default=8, ge=0, le=100)
    hard_count: int = Field(default=7, ge=0, le=100)

    @model_validator(mode="after")
    def validate_total(self):
        total = self.easy_count + self.medium_count + self.hard_count
        if total != 25:
            raise ValueError("Master paper must contain exactly 25 questions")
        if self.easy_count < 3:
            raise ValueError("Easy count must be at least 3 so all three fields can be represented")
        return self


class StatsResponse(BaseModel):
    total_staff: int
    total_tests: int
    pass_rate: float
    avg_score: float
    tests_this_month: int
    district_breakdown: List[Dict[str, Any]]
    topic_breakdown: List[Dict[str, Any]]
    question_bank_breakdown: List[Dict[str, Any]]
    recent_attempts: List[Dict[str, Any]]
    activity_log: List[Dict[str, Any]]


class LearningMaterialOut(BaseModel):
    id: int
    title: str
    filename: str
    content_type: str
    file_size: int
    uploaded_by_name: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
