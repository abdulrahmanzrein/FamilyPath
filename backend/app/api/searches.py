# /api/searches/* — start a search, poll its status, fetch final results.
# Also exposes the WebSocket route (no /api prefix per PRD §API).
#
# The HTTP routes are the integration contract the frontend binds to. The WS
# route is the live channel — fake_runner (and later the LangGraph supervisor)
# pushes events through hub.broadcast, this handler just keeps the socket
# subscribed for the lifetime of the search.

import asyncio
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.fake_runner import run_fake_search
from app.db.models import Search, SearchResult
from app.db.session import get_session
from app.schemas.searches import (
    AgentStatus,
    SearchResultsResponse,
    SearchStartRequest,
    SearchStartResponse,
    SearchStatusResponse,
)
from app.ws.hub import hub


router = APIRouter(prefix="/api/searches", tags=["searches"])

# the WS route lives at /ws/searches/{id} (no /api prefix per PRD), so it gets
# its own prefix-less router that main.py mounts separately
ws_router = APIRouter()


@router.post("/start", response_model=SearchStartResponse)
async def start_search(
    body: SearchStartRequest,
    session: AsyncSession = Depends(get_session),
) -> SearchStartResponse:
    # 1) persist the parent searches row FIRST and commit. fake_runner writes
    # search_results rows that FK back to this — if we don't commit before
    # spawning the task, the runner's first INSERT can race the parent row and
    # blow up with a foreign key violation.
    search = Search(
        user_name=body.name,
        phone=body.phone or None,
        postal_code=body.postal_code,
        language=body.language,
        insurance_type=body.insurance_type,
        status="running",
    )
    session.add(search)
    await session.commit()
    await session.refresh(search)

    # 2) fire and forget — return search_id immediately so the frontend can
    # open the websocket and start rendering. asyncio.create_task() schedules
    # run_fake_search on the event loop without awaiting it.
    asyncio.create_task(run_fake_search(search.search_id))

    return SearchStartResponse(search_id=search.search_id)


@router.get("/{search_id}/status", response_model=SearchStatusResponse)
async def get_search_status(
    search_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> SearchStatusResponse:
    # confirm the parent search exists so we can return 404 on bogus ids
    search = await session.get(Search, search_id)
    if search is None:
        raise HTTPException(status_code=404, detail="search not found")

    rows = (
        await session.execute(
            select(SearchResult).where(SearchResult.search_id == search_id)
        )
    ).scalars().all()

    agents = [
        AgentStatus(
            source=row.source,
            status=row.agent_status,  # already constrained to the status enum on insert
            clinic_name=row.clinic_name,
            message=None,  # message is event-only; not persisted on the row
            updated_at=row.updated_at,
        )
        for row in rows
    ]

    return SearchStatusResponse(
        search_id=search_id,
        overall_status=search.status,
        agents=agents,
    )


@router.get("/{search_id}/results", response_model=SearchResultsResponse)
async def get_search_results(
    search_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> SearchResultsResponse:
    search = await session.get(Search, search_id)
    if search is None:
        raise HTTPException(status_code=404, detail="search not found")

    rows = (
        await session.execute(
            select(SearchResult).where(SearchResult.search_id == search_id)
        )
    ).scalars().all()

    response = SearchResultsResponse(search_id=search_id)
    for row in rows:
        agent = AgentStatus(
            source=row.source,
            status=row.agent_status,
            clinic_name=row.clinic_name,
            message=None,
            updated_at=row.updated_at,
        )
        # per PRD §API: final output buckets on terminal/in-flight status.
        # confirmed = done + accepting; calling = still on the phone; failed = dead end.
        # rows still in pending/searching/found don't fit any final bucket — drop.
        if row.agent_status == "confirmed":
            response.confirmed.append(agent)
        elif row.agent_status == "calling":
            response.calling.append(agent)
        elif row.agent_status == "failed":
            response.failed.append(agent)

    return response


@ws_router.websocket("/ws/searches/{search_id}")
async def search_ws(websocket: WebSocket, search_id: UUID) -> None:
    # hub.connect calls websocket.accept() internally and registers the socket
    # under search_id so hub.broadcast pushes events to every dashboard tab
    # watching this search.
    await hub.connect(search_id, websocket)
    try:
        # the client doesn't need to send anything — receive_text() just blocks
        # until the socket closes. when it does, WebSocketDisconnect gets raised
        # and we fall into finally to clean up.
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        hub.disconnect(search_id, websocket)
