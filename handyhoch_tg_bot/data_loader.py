import json
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, TypedDict


class Listing(TypedDict):
    id: str
    title: str
    price_eur: int
    size_sqm: int
    rooms: int
    district: str
    available_from: str
    posted_at: str
    category: str  # wg | wohnung
    provider_type: str  # housing_association | private
    provider_name: str
    source: str  # platform or provider slug
    is_scam: bool
    url: str


def load_listings(path: Path) -> List[Listing]:
    if not path.exists():
        raise FileNotFoundError(f"Listings file not found: {path}")

    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    listings: List[Listing] = []
    for item in data:
        listing: Listing = {
            "id": str(item.get("id", "")).strip(),
            "title": str(item.get("title", "")).strip(),
            "price_eur": int(item.get("price_eur", 0)),
            "size_sqm": int(item.get("size_sqm", 0)),
            "rooms": int(item.get("rooms", 0)),
            "district": str(item.get("district", "")).strip(),
            "available_from": str(item.get("available_from", "")).strip(),
            "posted_at": str(item.get("posted_at", "")).strip(),
            "category": str(item.get("category", "")).strip().lower(),
            "provider_type": str(item.get("provider_type", "")).strip().lower(),
            "provider_name": str(item.get("provider_name", "")).strip(),
            "source": str(item.get("source", "")).strip().lower(),
            "is_scam": bool(item.get("is_scam", False)),
            "url": str(item.get("url", "")).strip(),
        }
        listings.append(listing)

    return listings


def shortlist(listings: Iterable[Listing], limit: int = 5) -> List[Listing]:
    def parse_posted_at(value: str) -> datetime:
        if not value:
            return datetime.min
        text = value.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            try:
                return datetime.strptime(text, "%Y-%m-%d")
            except ValueError:
                return datetime.min

    sorted_list = sorted(
        list(listings),
        key=lambda item: parse_posted_at(item.get("posted_at", "")),
        reverse=True,
    )
    return sorted_list[:limit]
