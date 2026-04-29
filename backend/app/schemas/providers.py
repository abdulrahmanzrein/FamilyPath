# read-only shape for /api/providers responses
# matches the providers DB table, with from_attributes so it can be built from a SQLAlchemy row

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ProviderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # lets us pass an ORM object directly

    provider_id: UUID
    clinic_name: str
    doctor_name: str | None
    address: str | None
    city: str | None
    postal_code: str | None
    lat: float | None
    lng: float | None
    phone: str | None
    languages: list[str]
    accepts_ifhp: bool | None
    accepts_ohip: bool | None
    accepting_new_patients: bool | None
    source: str
    last_scraped_at: datetime | None
