import asyncio
import json
import logging
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from core.awareness import event_queue

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/events")
async def event_stream(request: Request):
    async def generator():

        yield "data: {\"type\":\"ping\"}\n\n"
        while True:
            if await request.is_disconnected():
                break
            try:
                evt = await asyncio.wait_for(event_queue.get(), timeout=30)
                yield f"data: {json.dumps(evt)}\n\n"
            except asyncio.TimeoutError:

                yield "data: {\"type\":\"ping\"}\n\n"
            except Exception as e:
                logger.debug(f"SSE error: {e}")
                await asyncio.sleep(1)

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
