import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DECIMAL, Text, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base
from models.types import UUIDType, TZDateTime


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=uuid.uuid4)
    external_id: Mapped[str | None] = mapped_column(String(255))
    source: Mapped[str] = mapped_column(String(50), default="seed")
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    company_logo: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(255))
    is_remote: Mapped[bool] = mapped_column(Boolean, default=False)
    salary_min_lpa: Mapped[float | None] = mapped_column(DECIMAL(5, 2))
    salary_max_lpa: Mapped[float | None] = mapped_column(DECIMAL(5, 2))
    experience_min: Mapped[float] = mapped_column(DECIMAL(3, 1), default=0)
    experience_max: Mapped[float] = mapped_column(DECIMAL(3, 1), default=50)
    skills_required: Mapped[list] = mapped_column(JSON, default=list)
    description: Mapped[str | None] = mapped_column(Text)
    apply_url: Mapped[str | None] = mapped_column(Text)
    job_type: Mapped[str | None] = mapped_column(String(50))
    industry: Mapped[str | None] = mapped_column(String(100))
    # embedding_vector handled via raw SQL
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    posted_at: Mapped[datetime] = mapped_column(TZDateTime, default=lambda: datetime.now(timezone.utc))
    expires_at: Mapped[datetime | None] = mapped_column(TZDateTime)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=lambda: datetime.now(timezone.utc))

    swipes: Mapped[list["Swipe"]] = relationship(back_populates="job")
    applications: Mapped[list["Application"]] = relationship(back_populates="job")
