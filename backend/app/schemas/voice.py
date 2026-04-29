# shape ElevenLabs sends when the user interrupts mid-search
# e.g. "skip MCI, prioritize Appletree" -> { action: "skip", source: "mci" }

from typing import Literal

from pydantic import BaseModel


class VoiceInterruptRequest(BaseModel):
    action: Literal["skip", "prioritize", "cancel"]
    # required when action is skip/prioritize; optional for cancel — route handler enforces
    source: str | None = None  # odhf | cpso | appletree | mci | ifhp
