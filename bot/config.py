import os
from dataclasses import dataclass
from dotenv import load_dotenv
from zoneinfo import ZoneInfo

load_dotenv()

@dataclass(frozen=True)
class Config:
    bot_token: str = os.environ.get("BOT_TOKEN", "")
    api_base: str = os.environ.get("API_BASE", "http://localhost:8081")
    data_dir: str = os.environ.get("DATA_DIR", "./data")
    tz_moscow: ZoneInfo = ZoneInfo("Europe/Moscow")

CFG = Config()
