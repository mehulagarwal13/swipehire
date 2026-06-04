import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base
from models.types import UUIDType, TZDateTime


class Swipe(Base):
    __tablename__ = "swipes"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("users.id", ondelete="CASCADE"))
    job_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("jobs.id", ondelete="CASCADE"))
    direction: Mapped[str] = mapped_column(String(10), nullable=False)  # right | left | up
    match_score: Mapped[int | None] = mapped_column(Integer)
    swiped_at: Mapped[datetime] = mapped_column(TZDateTime, default=lambda: datetime.now(timezone.utc))

    user: Mapped["User"] = relationship(back_populates="swipes")
    job: Mapped["Job"] = relationship(back_populates="swipes")


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("users.id", ondelete="CASCADE"))
    job_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("jobs.id", ondelete="CASCADE"))
    swipe_id: Mapped[uuid.UUID | None] = mapped_column(UUIDType, ForeignKey("swipes.id"))
    status: Mapped[str] = mapped_column(String(50), default="applied")
    applied_at: Mapped[datetime] = mapped_column(TZDateTime, default=lambda: datetime.now(timezone.utc))
    auto_applied: Mapped[bool] = mapped_column(default=False)
    notes: Mapped[str | None] = mapped_column(String(2000))
    interview_date: Mapped[datetime | None] = mapped_column(TZDateTime)
    offer_amount: Mapped[float | None] = mapped_column()
    updated_at: Mapped[datetime] = mapped_column(TZDateTime, default=lambda: datetime.now(timezone.utc))

    user: Mapped["User"] = relationship(back_populates="applications")
    job: Mapped["Job"] = relationship(back_populates="applications")
