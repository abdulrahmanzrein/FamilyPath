# reads .env and gives us a typed `settings` object
# so we don't sprinkle os.getenv() all over the place

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # tells pydantic where to look for the env file
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # don't crash if .env has stuff we don't use
    )

    # required — server won't start without it
    database_url: str

    # blank defaults so this slice runs without filling these in yet
    anthropic_api_key: str = ""
    elevenlabs_api_key: str = ""
    elevenlabs_agent_id: str = ""
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""
    browserbase_api_key: str = ""
    browserbase_project_id: str = ""
    nexos_api_key: str = ""

    # vite dev server runs here — needed for CORS later
    cors_origins: list[str] = ["http://localhost:5173"]


# import this from anywhere: `from app.config import settings`
settings = Settings()
