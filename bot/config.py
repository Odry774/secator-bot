import os
from dataclasses import dataclass
from urllib.parse import urlparse

from dotenv import load_dotenv
from zoneinfo import ZoneInfo


_TRUTHY = {"1", "true", "yes", "on"}
_FALSY = {"0", "false", "no", "off"}


def _parse_bool(value: str | None) -> bool | None:
    if value is None:
        return None

    lowered = value.strip().lower()
    if lowered in _TRUTHY:
        return True
    if lowered in _FALSY:
        return False
    return None

load_dotenv()

@dataclass(frozen=True)
class Config:
    bot_token: str = os.environ.get("BOT_TOKEN", "")
    api_base: str = os.environ.get("API_BASE", "http://localhost:8081")
    data_dir: str = os.environ.get("DATA_DIR", "./data")
    tz_moscow: ZoneInfo = ZoneInfo("Europe/Moscow")

    @property
    def api_is_local(self) -> bool:
        override = _parse_bool(os.environ.get("API_LOCAL"))
        if override is not None:
            return override

        host = urlparse(self.api_base).hostname
        if not host:
            return False

        if host == "localhost" or host == "::1":
            return True

        if host.startswith("127."):
            return True

        return False

CFG = Config()
