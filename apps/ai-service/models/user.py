import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DECIMAL, Integer, Text, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base
from models.types import UUIDType, TZDateTime


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=uuid.uuid4)
    phone: Mapped[str | None] = mapped_column(String(15), unique=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    full_name: Mapped[str | None] = mapped_column(String(255))
    profile_photo: Mapped[str | None] = mapped_column(Text)
    plan: Mapped[str] = mapped_column(String(20), default="free")
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(TZDateTime, default=lambda: datetime.now(timezone.utc))

    profile: Mapped["UserProfile"] = relationship(back_populates="user", uselist=False)
    swipes: Mapped[list["Swipe"]] = relationship(back_populates="user")
    applications: Mapped[list["Application"]] = relationship(back_populates="user")


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    resume_url: Mapped[str | None] = mapped_column(Text)
    resume_text: Mapped[str | None] = mapped_column(Text)
    headline: Mapped[str | None] = mapped_column(String(255))
    skills: Mapped[list] = mapped_column(JSON, default=list)
    experience_years: Mapped[float] = mapped_column(DECIMAL(3, 1), default=0)
    current_location: Mapped[str | None] = mapped_column(String(100))
    preferred_locations: Mapped[list] = mapped_column(JSON, default=list)
    min_salary_lpa: Mapped[float | None] = mapped_column(DECIMAL(5, 2))
    max_salary_lpa: Mapped[float | None] = mapped_column(DECIMAL(5, 2))
    job_types: Mapped[list] = mapped_column(JSON, default=list)
    notice_period_days: Mapped[int] = mapped_column(Integer, default=30)
    education: Mapped[list] = mapped_column(JSON, default=list)
    experience: Mapped[list] = mapped_column(JSON, default=list)
    projects: Mapped[list] = mapped_column(JSON, default=list)
    certifications: Mapped[list] = mapped_column(JSON, default=list)
    # embedding_vector stored via raw SQL / pgvector; not mapped in ORM to avoid extension dep
    profile_score: Mapped[int] = mapped_column(Integer, default=0)
    is_onboarded: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(TZDateTime, default=lambda: datetime.now(timezone.utc))

    user: Mapped["User"] = relationship(back_populates="profile")
