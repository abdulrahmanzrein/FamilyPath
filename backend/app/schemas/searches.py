# request + response shapes for the /api/searches/* routes
# pydantic uses these to validate incoming JSON and serialize outgoing responses

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


# what the form sends when the user clicks "find me a doctor"
class SearchStartRequest(BaseModel):
    name: str  # PII — nexos.ai will strip this before any Claude call
    postal_code: str
    language: str
    insurance_type: Literal["ohip", "ifhp", "uhip", "waiting_period"]


# what we return immediately so the frontend can open the websocket
class SearchStartResponse(BaseModel):
    search_id: UUID


# one row per agent — what the dashboard needs to render a card
class AgentStatus(BaseModel):
    source: str  # odhf | cpso | appletree | mci | ifhp
    status: Literal["pending", "searching", "found", "calling", "confirmed", "failed"]
    clinic_name: str | None = None
    message: str | None = None
    updated_at: datetime


# polling endpoint response — frontend mostly uses websocket, this is a fallback
class SearchStatusResponse(BaseModel):
    search_id: UUID
    overall_status: str
    agents: list[AgentStatus]


# final shape after the search wraps up
class SearchResultsResponse(BaseModel):
    search_id: UUID
    confirmed: list[AgentStatus] = Field(default_factory=list)
    calling: list[AgentStatus] = Field(default_factory=list)
    failed: list[AgentStatus] = Field(default_factory=list)
