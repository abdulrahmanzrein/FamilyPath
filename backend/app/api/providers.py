# /api/providers — clinic lookup by FSA + language + insurance type.
# Reads the seeded providers table; the dashboard hits this for the map view
# and for "show me clinics near M5V that speak Punjabi and take IFHP".

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Provider
from app.db.session import get_session
from app.schemas.providers import ProviderResponse


router = APIRouter(prefix="/api/providers", tags=["providers"])


@router.get("/", response_model=list[ProviderResponse])
async def list_providers(
    postal_code: str | None = Query(default=None),
    language: str | None = Query(default=None),
    insurance_type: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> list[Provider]:
    stmt = select(Provider)

    # FSA = Forward Sortation Area, the first 3 chars of a Canadian postal code
    # (e.g. "L6V" in "L6V 4L1"). Matching on FSA gives us neighbourhood-level
    # filtering without requiring an exact full-postal match.
    if postal_code:
        fsa = postal_code.strip().upper()[:3]
        stmt = stmt.where(Provider.postal_code.startswith(fsa))

    if language:
        # languages is a Postgres TEXT[]; .contains([x]) emits the @> operator
        # ("array contains all of these elements"), so this is "row's languages
        # array includes this language".
        stmt = stmt.where(Provider.languages.contains([language]))

    # Only filter on the two insurance types we actually persist booleans for.
    # uhip / waiting_period aren't tracked at the provider level — they're
    # search-level facts, not clinic-level — so we silently ignore them here.
    if insurance_type == "ifhp":
        stmt = stmt.where(Provider.accepts_ifhp.is_(True))
    elif insurance_type == "ohip":
        stmt = stmt.where(Provider.accepts_ohip.is_(True))

    rows = (await session.execute(stmt)).scalars().all()
    # response_model=list[ProviderResponse] + ConfigDict(from_attributes=True)
    # on the schema means FastAPI serializes the ORM rows directly.
    return rows
