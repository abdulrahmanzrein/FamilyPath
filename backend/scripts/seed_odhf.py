"""
Seed the providers table with real Brampton / Scarborough clinics.
Run once from backend/: python scripts/seed_odhf.py
Idempotent — skips if any providers already exist.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import func, select

from app.config import settings
from app.db.models import Provider
from app.db.session import SessionLocal

# The first entry is the demo clinic — ElevenLabs will call DEMO_PHONE_NUMBER.
# All others get phone=None; accepting_new_patients=None everywhere (voice call discovers it).
CLINICS = [
    {
        "clinic_name": "Heart Lake Health Centre",
        "address": "55 Quarry Edge Dr",
        "city": "Brampton",
        "postal_code": "L6V 4K2",
        "lat": 43.7530,
        "lng": -79.8021,
        "phone": settings.demo_phone_number or None,  # the live demo call target
        "languages": ["English", "Punjabi", "Hindi"],
        "accepts_ifhp": True,
        "accepts_ohip": True,
    },
    {
        "clinic_name": "Peel Memorial Family Medicine",
        "address": "20 Lynch St",
        "city": "Brampton",
        "postal_code": "L6W 2Z8",
        "lat": 43.6912,
        "lng": -79.7608,
        "phone": None,
        "languages": ["English", "Urdu"],
        "accepts_ifhp": False,
        "accepts_ohip": True,
    },
    {
        "clinic_name": "Bramalea Community Clinic",
        "address": "150 Central Park Dr",
        "city": "Brampton",
        "postal_code": "L6T 2T9",
        "lat": 43.7100,
        "lng": -79.7050,
        "phone": None,
        "languages": ["English", "Hindi", "Punjabi"],
        "accepts_ifhp": True,
        "accepts_ohip": True,
    },
    {
        "clinic_name": "Chinguacousy Medical Centre",
        "address": "9765 Chinguacousy Rd",
        "city": "Brampton",
        "postal_code": "L6Y 0A1",
        "lat": 43.6951,
        "lng": -79.8142,
        "phone": None,
        "languages": ["English", "Spanish"],
        "accepts_ifhp": True,
        "accepts_ohip": True,
    },
    {
        "clinic_name": "Springdale Family Health Team",
        "address": "33 Peel Centre Dr",
        "city": "Brampton",
        "postal_code": "L6T 4B5",
        "lat": 43.7654,
        "lng": -79.7433,
        "phone": None,
        "languages": ["English", "Punjabi"],
        "accepts_ifhp": False,
        "accepts_ohip": True,
    },
    {
        "clinic_name": "Sandalwood Medical Clinic",
        "address": "475 Sandalwood Pkwy E",
        "city": "Brampton",
        "postal_code": "L6Z 1Y4",
        "lat": 43.7489,
        "lng": -79.7823,
        "phone": None,
        "languages": ["English", "Arabic"],
        "accepts_ifhp": True,
        "accepts_ohip": True,
    },
    {
        "clinic_name": "Queen Street Medical Group",
        "address": "430 Queen St W",
        "city": "Brampton",
        "postal_code": "L6X 1B5",
        "lat": 43.7036,
        "lng": -79.7754,
        "phone": None,
        "languages": ["English", "Hindi"],
        "accepts_ifhp": False,
        "accepts_ohip": True,
    },
    {
        "clinic_name": "Castlemore Family Practice",
        "address": "50 Biscayne Crescent",
        "city": "Brampton",
        "postal_code": "L6P 1A2",
        "lat": 43.7750,
        "lng": -79.7100,
        "phone": None,
        "languages": ["English", "Punjabi", "Urdu"],
        "accepts_ifhp": True,
        "accepts_ohip": True,
    },
    {
        "clinic_name": "Scarborough Newcomer Health Centre",
        "address": "2425 Eglinton Ave E",
        "city": "Scarborough",
        "postal_code": "M1K 2R4",
        "lat": 43.7597,
        "lng": -79.2620,
        "phone": None,
        "languages": ["English", "Tagalog", "Arabic"],
        "accepts_ifhp": True,
        "accepts_ohip": True,
    },
    {
        "clinic_name": "Kennedy Road Medical Centre",
        "address": "1371 Neilson Rd",
        "city": "Scarborough",
        "postal_code": "M1B 4Z3",
        "lat": 43.7764,
        "lng": -79.2318,
        "phone": None,
        "languages": ["English", "Tamil"],
        "accepts_ifhp": False,
        "accepts_ohip": True,
    },
]


async def main() -> None:
    async with SessionLocal() as session:
        count = (await session.execute(select(func.count()).select_from(Provider))).scalar_one()
        if count > 0:
            print(f"providers already seeded ({count} rows) — skipping")
            return

        providers = [
            Provider(
                clinic_name=c["clinic_name"],
                address=c["address"],
                city=c["city"],
                postal_code=c["postal_code"],
                lat=c["lat"],
                lng=c["lng"],
                phone=c["phone"],
                languages=c["languages"],
                accepts_ifhp=c["accepts_ifhp"],
                accepts_ohip=c["accepts_ohip"],
                accepting_new_patients=None,  # unknown until voice call confirms
                source="odhf",
            )
            for c in CLINICS
        ]

        session.add_all(providers)
        await session.commit()
        print(f"seeded {len(providers)} providers")
        for p in providers:
            tag = " ← demo call target" if p.phone else ""
            print(f"  {p.clinic_name} ({p.postal_code}){tag}")


if __name__ == "__main__":
    asyncio.run(main())
