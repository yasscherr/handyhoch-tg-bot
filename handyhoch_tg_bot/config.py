from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv


@dataclass
class Settings:
    bot_token: str
    listings_path: Path


def load_settings() -> Settings:
    load_dotenv()

    bot_token = os.getenv("BOT_TOKEN", "").strip()
    if not bot_token:
        raise ValueError("BOT_TOKEN is required. Add it to your environment or .env file.")

    listings_path = Path(os.getenv("LISTINGS_PATH", "data/listings.json")).expanduser()
    return Settings(bot_token=bot_token, listings_path=listings_path)
