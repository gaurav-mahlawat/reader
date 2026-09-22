from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    host: str = "127.0.0.1"
    port: int = 8000
    data_dir: str = "data"
    headless_default: bool = False

    @property
    def data_path(self) -> Path:
        path = PROJECT_ROOT / self.data_dir
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def session_path(self) -> Path:
        return self.data_path / "session.json"

    @property
    def session_email_path(self) -> Path:
        return self.data_path / "session_email.txt"

    @property
    def db_path(self) -> Path:
        return self.data_path / "bids.db"


settings = Settings()
