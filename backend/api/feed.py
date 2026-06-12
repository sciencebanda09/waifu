from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from core.growth import GrowthEngine, FOOD_TYPES
from core.personality import apply_personality_event
from core.memory import MemoryEngine

router  = APIRouter()
_growth = GrowthEngine()
_mem    = MemoryEngine()


class FeedRequest(BaseModel):
    food_type: Optional[str] = "snack"


@router.post("/feed")
async def feed(request: FeedRequest):
    food_type = request.food_type or "snack"
    if food_type not in FOOD_TYPES:
        food_type = "snack"

    result = await _growth.feed(food_type)
    await apply_personality_event("fed")
    await _mem.remember("feed", f"was fed a {food_type}", importance=1)
    return result
