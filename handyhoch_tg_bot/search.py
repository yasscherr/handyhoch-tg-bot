from datetime import datetime, timedelta, timezone
from typing import Iterable, List, Optional, Sequence

from .data_loader import Listing


def normalize_districts(districts: Optional[Sequence[str]]) -> Optional[List[str]]:
    if not districts:
        return None
    normalized = [district.strip().lower() for district in districts if district.strip()]
    return normalized or None


HOUSING_ASSOCIATIONS = {
    "gewobag",
    "howoge",
    "degewo",
    "stadt und land",
    "berlinovo",
    "wgl",
}

PRIVATE_SOURCES = {
    "wggesucht",
    "kleinanzeigen",
    "immoscout",
}

VALID_CATEGORIES = {"wg", "wohnung"}
VALID_PROVIDER_TYPES = {"housing_association", "private"}

DEFAULT_MAX_AGE_HOURS = 5.0


def _parse_posted_at(value: str) -> datetime:
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)
    text = value.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        try:
            dt = datetime.strptime(text, "%Y-%m-%d")
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return datetime.min.replace(tzinfo=timezone.utc)

def filter_listings(
    listings: Iterable[Listing],
    *,
    max_rent: Optional[int] = None,
    districts: Optional[Sequence[str]] = None,
    min_rooms: Optional[int] = None,
    category: Optional[str] = None,
    provider_type: Optional[str] = None,
    exclude_suspected_scam: bool = False,
    max_age_hours: Optional[float] = DEFAULT_MAX_AGE_HOURS,
    now: Optional[datetime] = None,
) -> List[Listing]:
    allowed_districts = normalize_districts(districts)
    normalized_category = category.strip().lower() if category else None
    normalized_provider = provider_type.strip().lower() if provider_type else None
    now_dt = now or datetime.now(timezone.utc)
    if now_dt.tzinfo is None:
        now_dt = now_dt.replace(tzinfo=timezone.utc)
    cutoff = None
    if max_age_hours is not None:
        cutoff = now_dt - timedelta(hours=max_age_hours)

    def matches(listing: Listing) -> bool:
        if max_rent is not None and listing["price_eur"] > max_rent:
            return False
        if min_rooms is not None and listing["rooms"] < min_rooms:
            return False
        if allowed_districts and listing["district"].strip().lower() not in allowed_districts:
            return False
        if normalized_category and listing.get("category") != normalized_category:
            return False
        if normalized_provider:
            if listing.get("provider_type") != normalized_provider:
                return False
            if normalized_provider == "housing_association":
                if listing.get("provider_name", "").strip().lower() not in HOUSING_ASSOCIATIONS:
                    return False
            if normalized_provider == "private":
                if listing.get("source", "").strip().lower() not in PRIVATE_SOURCES:
                    return False
        if exclude_suspected_scam and listing.get("is_scam"):
            return False
        if cutoff:
            posted_at = _parse_posted_at(listing.get("posted_at", ""))
            if posted_at < cutoff:
                return False
        return True

    return sorted(
        (listing for listing in listings if matches(listing)),
        key=lambda item: _parse_posted_at(item.get("posted_at", "")),
        reverse=True,
    )


def format_listing(listing: Listing) -> str:
    move_in = listing.get("available_from") or "—"
    try:
        parsed = datetime.strptime(move_in, "%Y-%m-%d")
        move_in = parsed.strftime("%d.%m.%Y")
    except ValueError:
        move_in = move_in or "—"

    provider = listing.get("provider_name", "—")
    provider_type = listing.get("provider_type", "")
    provider_label = "Wohnbaugesellschaft" if provider_type == "housing_association" else "Частник"
    source = listing.get("source", "—")
    category = listing.get("category", "").upper() or "—"
    scam_hint = "⚠️ Возможный скам" if listing.get("is_scam") else ""

    return (
        f"[{category}] {listing['title']} ({listing['district']})\n"
        f"Цена: €{listing['price_eur']} · Комнат: {listing['rooms']} · {listing['size_sqm']} m²\n"
        f"Заезд с: {move_in} · Провайдер: {provider_label} ({provider}) · Источник: {source}\n"
        f"{' '.join(filter(None, [scam_hint]))}\n"
        f"Ссылка: {listing['url']}"
    )
