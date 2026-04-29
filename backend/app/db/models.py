# the three DB tables, matching the schema in prd.md
# providers = clinics + doctors we know about
# searches = one row per user request
# search_results = per-agent rows, one per source per search

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Provider(Base):
    __tablename__ = "providers"

    provider_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    clinic_name: Mapped[str] = mapped_column(String)
    doctor_name: Mapped[str | None] = mapped_column(String, nullable=True)  # null for clinic-level rows
    address: Mapped[str | None] = mapped_column(String, nullable=True)
    city: Mapped[str | None] = mapped_column(String, nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String, nullable=True)
    lat: Mapped[float | None] = mapped_column(nullable=True)
    lng: Mapped[float | None] = mapped_column(nullable=True)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    languages: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)  # e.g. ["Punjabi", "English"]
    accepts_ifhp: Mapped[bool | None] = mapped_column(nullable=True)
    accepts_ohip: Mapped[bool | None] = mapped_column(nullable=True)
    accepting_new_patients: Mapped[bool | None] = mapped_column(nullable=True)  # null = unknown, voice call confirms
    source: Mapped[str] = mapped_column(String)  # odhf | cpso | appletree | mci | ifhp
    last_scraped_at: Mapped[datetime | None] = mapped_column(nullable=True)


class Search(Base):
    __tablename__ = "searches"

    search_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_name: Mapped[str] = mapped_column(String)  # PII — nexos.ai strips this before any Claude call
    postal_code: Mapped[str] = mapped_column(String)
    language: Mapped[str] = mapped_column(String)
    insurance_type: Mapped[str] = mapped_column(String)  # ohip | ifhp | uhip | waiting_period
    status: Mapped[str] = mapped_column(String, default="pending")  # pending | running | completed | failed
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)


class SearchResult(Base):
    __tablename__ = "search_results"

    result_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    search_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("searches.search_id"))
    provider_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("providers.provider_id"), nullable=True
    )
    agent_status: Mapped[str] = mapped_column(String, default="pending")
    # ^ pending | searching | found | calling | confirmed | failed
    call_transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    confirmed_accepting: Mapped[bool | None] = mapped_column(nullable=True)  # set after voice call
    source: Mapped[str] = mapped_column(String)  # which agent reported this row
    clinic_name: Mapped[str | None] = mapped_column(String, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
