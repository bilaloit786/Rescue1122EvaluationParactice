from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, JSON, Text, Enum, Table, LargeBinary
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class UserRole(str, enum.Enum):
    admin = "admin"
    staff = "staff"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default="staff", nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    profile = relationship("StaffProfile", back_populates="user", uselist=False, cascade="all, delete-orphan", lazy="selectin")
    test_attempts = relationship("TestAttempt", back_populates="user", cascade="all, delete-orphan", lazy="selectin")


class StaffProfile(Base):
    __tablename__ = "staff_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    full_name = Column(String(200), nullable=False)
    father_name = Column(String(200))
    designation = Column(String(100), nullable=False)
    district = Column(String(100), nullable=False)
    station = Column(String(100))
    employee_id = Column(String(50))
    phone = Column(String(20))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="profile")


class TestAttempt(Base):
    __tablename__ = "test_attempts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    topic_id = Column(String(100), nullable=False)
    topic_label = Column(String(200), nullable=False)
    total_questions = Column(Integer, default=25)
    correct_answers = Column(Integer, default=0)
    score_percent = Column(Float, default=0.0)
    passed = Column(Boolean, default=False)
    time_taken_seconds = Column(Integer)
    answers = Column(JSON)           # [{q_index, selected, correct}]
    questions = Column(JSON)         # full question objects
    subtopic_scores = Column(JSON)   # {subtopic: {correct, total}}
    ai_feedback = Column(Text)
    email_sent = Column(Boolean, default=False)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="test_attempts")


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    actor_id = Column(Integer, nullable=True, index=True)
    actor_name = Column(String(200), nullable=True)
    action = Column(String(80), nullable=False, index=True)
    entity_type = Column(String(80), nullable=False, index=True)
    entity_id = Column(Integer, nullable=True, index=True)
    description = Column(String(500), nullable=False)
    details = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class LearningMaterial(Base):
    __tablename__ = "learning_materials"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    filename = Column(String(255), nullable=False)
    content_type = Column(String(100), default="application/pdf", nullable=False)
    file_size = Column(Integer, nullable=False)
    file_data = Column(LargeBinary, nullable=False)
    uploaded_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    uploaded_by_name = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class MasterTestPaper(Base):
    __tablename__ = "master_test_papers"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    total_questions = Column(Integer, default=25, nullable=False)
    easy_count = Column(Integer, default=10, nullable=False)
    medium_count = Column(Integer, default=8, nullable=False)
    hard_count = Column(Integer, default=7, nullable=False)
    questions = Column(JSON, nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_by_name = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


staff_seen_questions = Table(
    "staff_seen_questions",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("question_id", Integer, ForeignKey("question_bank.id", ondelete="CASCADE"), primary_key=True)
)


active_test_questions = Table(
    "active_test_questions",
    Base.metadata,
    Column("question_id", Integer, ForeignKey("question_bank.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("topic_id", String(100), nullable=False, index=True),
    Column("reserved_at", DateTime(timezone=True), server_default=func.now()),
    Column("expires_at", DateTime(timezone=True), nullable=False, index=True),
)


class QuestionBank(Base):
    __tablename__ = "question_bank"

    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(String(100), nullable=False, index=True)
    difficulty = Column(String(20), nullable=False)
    question = Column(JSON, nullable=False)
    is_valid = Column(Boolean, default=True, nullable=False, index=True)
    times_served = Column(Integer, default=0)
    times_wrong = Column(Integer, default=0)
