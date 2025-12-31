from handyhoch_tg_bot.data_loader import Listing
from handyhoch_tg_bot.search import filter_listings, format_listing, normalize_districts


def sample_listings() -> list[Listing]:
    return [
        {
            "id": "1",
            "title": "Test A",
            "price_eur": 1000,
            "size_sqm": 40,
            "rooms": 2,
            "district": "Friedrichshain",
            "available_from": "2025-01-01",
            "posted_at": "2025-01-11T10:00:00+00:00",
            "category": "wg",
            "provider_type": "private",
            "provider_name": "Privat",
            "source": "wggesucht",
            "is_scam": False,
            "url": "http://example.com/a",
        },
        {
            "id": "2",
            "title": "Test B",
            "price_eur": 1500,
            "size_sqm": 60,
            "rooms": 3,
            "district": "Neukölln",
            "available_from": "2025-02-15",
            "posted_at": "2025-01-10T12:00:00+00:00",
            "category": "wohnung",
            "provider_type": "housing_association",
            "provider_name": "Degewo",
            "source": "degewo",
            "is_scam": False,
            "url": "http://example.com/b",
        },
        {
            "id": "3",
            "title": "Test Scam",
            "price_eur": 700,
            "size_sqm": 20,
            "rooms": 1,
            "district": "Mitte",
            "available_from": "2025-02-01",
            "posted_at": "2025-01-12T11:00:00+00:00",
            "category": "wg",
            "provider_type": "private",
            "provider_name": "Privat",
            "source": "wggesucht",
            "is_scam": True,
            "url": "http://example.com/c",
        },
    ]


def test_normalize_districts():
    assert normalize_districts(["Friedrichshain", " Mitte "]) == ["friedrichshain", "mitte"]
    assert normalize_districts([]) is None
    assert normalize_districts(None) is None


def test_filter_by_budget_and_rooms():
    listings = sample_listings()
    filtered = filter_listings(listings, max_rent=1200, min_rooms=2, max_age_hours=None)
    assert len(filtered) == 1
    assert filtered[0]["id"] == "1"


def test_filter_by_district():
    listings = sample_listings()
    filtered = filter_listings(listings, districts=["NEUKÖLLN"], max_age_hours=None)
    assert len(filtered) == 1
    assert filtered[0]["district"] == "Neukölln"


def test_filter_by_category_and_provider_type():
    listings = sample_listings()
    filtered = filter_listings(
        listings,
        category="wohnung",
        provider_type="housing_association",
        now=__import__("datetime").datetime.fromisoformat("2025-01-12T12:00:00"),
        max_age_hours=None,
    )
    assert len(filtered) == 1
    assert filtered[0]["provider_name"] == "Degewo"


def test_filter_exclude_scam():
    listings = sample_listings()
    filtered = filter_listings(
        listings,
        category="wg",
        provider_type="private",
        exclude_suspected_scam=True,
        now=__import__("datetime").datetime.fromisoformat("2025-01-12T12:00:00"),
        max_age_hours=None,
    )
    assert all(not item["is_scam"] for item in filtered)


def test_filter_by_age_hours():
    listings = sample_listings()
    filtered = filter_listings(
        listings,
        category="wg",
        provider_type="private",
        max_age_hours=36,
        now=__import__("datetime").datetime.fromisoformat("2025-01-12T12:00:00"),
    )
    ids = [item["id"] for item in filtered]
    assert "1" in ids and "3" in ids

    filtered_short = filter_listings(
        listings,
        category="wg",
        provider_type="private",
        max_age_hours=2,
        now=__import__("datetime").datetime.fromisoformat("2025-01-12T12:00:00"),
    )
    assert [item["id"] for item in filtered_short] == ["3"]


def test_format_listing_includes_fields():
    listing = sample_listings()[0]
    text = format_listing(listing)
    assert "Test A" in text
    assert "Friedrichshain" in text
    assert "€1000" in text
