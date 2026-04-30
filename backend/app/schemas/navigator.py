from typing import Literal

from pydantic import BaseModel, Field


class NavigatorMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=12_000)


class NavigatorChatRequest(BaseModel):
    messages: list[NavigatorMessage] = Field(..., min_length=1, max_length=24)
    language: str | None = None
    insurance_type: str | None = None


class NavigatorChatResponse(BaseModel):
    reply: str
