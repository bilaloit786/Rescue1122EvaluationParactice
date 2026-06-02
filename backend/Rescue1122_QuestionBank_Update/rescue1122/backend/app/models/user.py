from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id               = Column(Integer, primary_key=True, index=True)
    email            = Column(String(255), unique=True, index=True, nullable=False)
    username         = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password  = Column(String(255), nullable=False)
    role             = Column(String(20), default="staff", nullable=False)
    is_active        = Column(Boolean, default=True)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())
    updated_at       = Column(DateTime(timezone=True), onupdate=func.now())

    profile        = relationship("StaffProfile",       back_populates="user", uselist=False, cascade="all, delete-orphan")
    test_attempts  = relationship("TestAttempt",        back_populates="user", cascade="all, delete-orphan")
    seen_questions = relationship("StaffSeenQuestion",  back_populates="user", cascade="all, delete-orphan")


class StaffProfile(Base):
    __tablename__ = "staff_profiles"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    full_name   = Column(String(200), nullable=False)
    father_name = Column(String(200))
    designation = Column(String(100), nullable=False)
    district    = Column(String(100), nullable=False)
    station     = Column(String(100))
    employee_id = Column(String(50))
    phone       = Column(String(20))
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="profile")


class TestAttempt(Base):
    __tablename__ = "test_attempts"

    id                 = Column(Integer, primary_key=True, index=True)
    user_id            = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    topic_id           = Column(String(100), nullable=False)
    topic_label        = Column(String(200), nullable=False)
    total_questions    = Column(Integer, default=25)
    correct_answers    = Column(Integer, default=0)
    score_percent      = Column(Float, default=0.0)
    passed             = Column(Boolean, default=False)
    time_taken_seconds = Column(Integer)
    answers            = Column(JSON)
    questions          = Column(JSON)
    subtopic_scores    = Column(JSON)
    ai_feedback        = Column(Text)
    email_sent         = Column(Boolean, default=False)
    started_at         = Column(DateTime(timezone=True))
    completed_at       = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="test_attempts")


class QuestionBank(Base):
    """Pre-generated MCQs from official Rescue 1122 source books."""
    __tablename__ = "question_bank"

    id           = Column(Integer, primary_key=True, index=True)
    topic_id     = Column(String(100), nullable=False, index=True)
    topic_label  = Column(String(200), nullable=False)
    subtopic     = Column(String(200))
    difficulty   = Column(String(20), default="medium", index=True)
    question     = Column(Text, nullable=False)
    option_a     = Column(Text, nullable=False)
    option_b     = Column(Text, nullable=False)
    option_c     = Column(Text, nullable=False)
    option_d     = Column(Text, nullable=False)
    correct_ans  = Column(Integer, nullable=False)
    source_doc   = Column(String(300))
    times_served = Column(Integer, default=0)
    times_wrong  = Column(Integer, default=0)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())

    seen_by = relationship("StaffSeenQuestion", back_populates="question", cascade="all, delete-orphan")


class StaffSeenQuestion(Base):
    """Tracks which questions each staff member has already seen — ensures uniqueness."""
    __tablename__ = "staff_seen_questions"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, ForeignKey("users.id",         ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("question_bank.id", ondelete="CASCADE"), nullable=False, index=True)
    seen_at     = Column(DateTime(timezone=True), server_default=func.now())

    user     = relationship("User",         back_populates="seen_questions")
    question = relationship("QuestionBank", back_populates="seen_by")
