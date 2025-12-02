"""
SQLAlchemy ORM models for candidate-related tables.
These map to the PostgreSQL tables created by 01_schema.sql

IMPLEMENTED:
- Job model with AI ranking fields
"""

from sqlalchemy import Column, String, Integer, Numeric, DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.database import Base


class Candidate(Base):
    """Main candidate table."""

    __tablename__ = "candidate"
    __table_args__ = {"schema": "rightstaff"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name = Column(Text, nullable=False)
    years_experience = Column(Numeric(5, 2))
    professional_summary = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships (for eager loading with joins)
    contact = relationship("CandidateContact", back_populates="candidate", uselist=False)
    preference = relationship("CandidatePreference", back_populates="candidate", uselist=False)
    demographics = relationship("CandidateDemographics", back_populates="candidate", uselist=False)
    resumes = relationship("CandidateResume", back_populates="candidate")
    skills = relationship("CandidateSkill", back_populates="candidate")
    applications = relationship("Application", back_populates="candidate")


class CandidateContact(Base):
    """Candidate contact information."""

    __tablename__ = "candidate_contact"
    __table_args__ = {"schema": "rightstaff"}

    candidate_id = Column(
        UUID(as_uuid=True), ForeignKey("rightstaff.candidate.id", ondelete="CASCADE"), primary_key=True
    )
    email = Column(String)
    phone = Column(String)
    address_line1 = Column(Text)
    address_line2 = Column(Text)
    city = Column(Text)
    region = Column(Text)
    postal_code = Column(String)
    country = Column(String)

    candidate = relationship("Candidate", back_populates="contact")


class CandidatePreference(Base):
    """Candidate work preferences and requirements."""

    __tablename__ = "candidate_preference"
    __table_args__ = {"schema": "rightstaff"}

    candidate_id = Column(
        UUID(as_uuid=True), ForeignKey("rightstaff.candidate.id", ondelete="CASCADE"), primary_key=True
    )
    work_authorization = Column(Text)  # US Citizen, Green Card, H1B, OPT, etc.
    work_arrangement = Column(
        SQLEnum(
            'Remote', 'Hybrid', 'On-site',
            schema="rightstaff",
            name="work_arrangement_enum"
        ),
        nullable=True
    )  # Remote, Hybrid, On-site
    willing_to_relocate = Column(Text)  # Yes, No, or specific locations
    desired_salary_min = Column(Numeric(12, 2))
    desired_salary_max = Column(Numeric(12, 2))
    salary_currency = Column(String(3), default='USD')
    salary_period = Column(Text, default='year')  # year, hour, etc.
    availability_start = Column(Text)  # When can they start
    open_to_remote = Column(Boolean)

    candidate = relationship("Candidate", back_populates="preference")


class CandidateDemographics(Base):
    """Candidate demographic information (EEO/sensitive data)."""

    __tablename__ = "candidate_demographics"
    __table_args__ = {"schema": "rightstaff"}

    candidate_id = Column(
        UUID(as_uuid=True), ForeignKey("rightstaff.candidate.id", ondelete="CASCADE"), primary_key=True
    )
    disability = Column(Text)  # Yes, No, or description
    ethnicity = Column(Text)
    veteran_status = Column(Text)  # Yes, No, or type
    collected_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    candidate = relationship("Candidate", back_populates="demographics")


class CandidateResume(Base):
    """Candidate resume files (stored in S3/MinIO)."""

    __tablename__ = "candidate_resume"
    __table_args__ = {"schema": "rightstaff"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("rightstaff.candidate.id", ondelete="CASCADE"), nullable=False)
    s3_url = Column(Text, nullable=False)
    file_type = Column(String)
    is_latest = Column(Boolean, default=True, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    candidate = relationship("Candidate", back_populates="resumes")

# ========================================
# NEW: Skill Model
# ========================================


class Skill(Base):
    """Skills ontology with parent-child relationships."""

    __tablename__ = "skill"
    __table_args__ = {"schema": "rightstaff"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False, unique=True)
    parent_skill_id = Column(UUID(as_uuid=True), ForeignKey("rightstaff.skill.id", ondelete="SET NULL"))


class CandidateSkill(Base):
    """Many-to-many relationship between candidates and skills."""

    __tablename__ = "candidate_skill"
    __table_args__ = {"schema": "rightstaff"}

    candidate_id = Column(
        UUID(as_uuid=True), ForeignKey("rightstaff.candidate.id", ondelete="CASCADE"), primary_key=True
    )
    skill_id = Column(UUID(as_uuid=True), ForeignKey("rightstaff.skill.id", ondelete="CASCADE"), primary_key=True)
    level = Column(Text)
    years = Column(Numeric(5, 2))

    candidate = relationship("Candidate", back_populates="skills")


# ========================================
# NEW: Job Model
# ========================================


class WorkArrangement(str, enum.Enum):
    """Work arrangement enumeration - matches database work_arrangement_enum."""

    remote = "Remote"
    hybrid = "Hybrid"
    onsite = "On-site"


class JobStatus(str, enum.Enum):
    """Job status enumeration."""

    draft = "draft"
    open = "open"
    closed = "closed"
    cancelled = "cancelled"


class Job(Base):
    """
    Job posting table with AI ranking fields.

    Fields for AI ranking:
    - description: Job description text (for semantic search)
    - required_skills_json: All skills mentioned in JD
    - must_have_skills_json: Non-negotiable skills (SQL gate)
    - min/max_years_experience: Experience requirements
    - work_arrangement: Remote/hybrid/onsite
    - employment_type: Full-time/part-time/contract
    """

    __tablename__ = "job"
    __table_args__ = {"schema": "rightstaff"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(Text, nullable=False)
    description = Column(Text)
    department = Column(Text)
    location = Column(Text)
    status = Column(
        SQLEnum(JobStatus, schema="rightstaff", name="job_status_enum"), nullable=False, default=JobStatus.draft
    )

    # AI ranking fields
    required_skills_json = Column(JSONB)
    must_have_skills_json = Column(JSONB)
    min_years_experience = Column(Numeric(5, 2))
    max_years_experience = Column(Numeric(5, 2))
    work_arrangement = Column(String)
    employment_type = Column(String)

    # Additional filter fields for chatbot & ranking
    is_remote = Column(Boolean, default=False, nullable=False)
    visa_sponsorship_available = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    applications = relationship("Application", back_populates="job")


# ========================================
# Application Model - Job Applications
# ========================================

class ApplicationStatus(str, enum.Enum):
    """
    Application status enumeration.
    Matches database enum: application_status_enum
    """
    sourced = "sourced"
    applied = "applied"
    screen = "screen"
    shortlist = "shortlist"
    interview = "interview"
    offer = "offer"
    hired = "hired"
    rejected = "rejected"
    withdrawn = "withdrawn"


class Application(Base):
    """
    Job applications - tracks which candidates applied to which jobs.

    BUSINESS RULES:
    - One candidate can apply to a job only ONCE (UNIQUE constraint)
    - Application status tracks hiring pipeline stage
    - Foreign keys CASCADE on delete (delete candidate → delete applications)

    USAGE:
        # Create application
        app = Application(
            candidate_id=candidate.id,
            job_id=job.id,
            status=ApplicationStatus.applied
        )

        # Get all applicants for a job
        job.applications  # List[Application]

        # Get all jobs a candidate applied to
        candidate.applications  # List[Application]
    """

    __tablename__ = "application"
    __table_args__ = {"schema": "rightstaff"}

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign keys
    candidate_id = Column(
        UUID(as_uuid=True),
        ForeignKey("rightstaff.candidate.id", ondelete="CASCADE"),
        nullable=False
    )
    job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("rightstaff.job.id", ondelete="CASCADE"),
        nullable=False
    )

    # Status tracking
    status = Column(
        SQLEnum(
            ApplicationStatus,
            schema="rightstaff",
            name="application_status_enum"
        ),
        nullable=False,
        default=ApplicationStatus.applied
    )

    # Timestamps
    applied_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships (bidirectional)
    candidate = relationship("Candidate", back_populates="applications")
    job = relationship("Job", back_populates="applications")
