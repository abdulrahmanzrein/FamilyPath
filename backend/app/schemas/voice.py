# shape ElevenLabs sends when the user interrupts mid-search
# e.g. "skip MCI, prioritize Appletree" -> { action: "skip", source: "mci" }

from typing import Literal

from pydantic import BaseModel


class VoiceInterruptRequest(BaseModel):
    action: Literal["skip", "prioritize", "cancel"]
    source: str  # odhf | cpso | appletree | mci | ifhp
