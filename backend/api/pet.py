from fastapi import APIRouter
from datetime import datetime

from core.database import get_pet_state, update_pet_state
from core.growth import GrowthEngine
from core.personality import apply_personality_event, compute_mood, get_personality
from core.memory import MemoryEngine

router  = APIRouter()
_growth = GrowthEngine()
_mem    = MemoryEngine()


@router.post("/pet")
async def pet_action():
    state       = await get_pet_state()
    personality = await get_personality()

    await apply_personality_event("petted")
    await _growth.update_trust_affection(trust_delta=1, aff_delta=3)

    xp_result = await _growth.add_xp("pet")
    new_mood   = await compute_mood(personality, state)
    await update_pet_state(
        current_mood=new_mood,
        last_petted=datetime.utcnow().isoformat(),
    )

    await _mem.remember("interaction", "user petted her", importance=1, emotion=new_mood)

    return {
        "mood":      new_mood,
        "xp_gained": xp_result["xp_gained"],
        "message":   "*she seems pleased*",
        "trust":     min(100, state.get("trust", 0) + 1),
        "affection": min(100, state.get("affection", 0) + 3),
    }


from pydantic import BaseModel as _BaseModel2

class OutfitRequest(_BaseModel2):
    outfit: str

@router.post('/outfit')
async def set_outfit(request: OutfitRequest):
    valid = ['seifuku','seifuku2','sundress','hoodie','pjs','swimsuit','coat','pe uniform']
    if request.outfit not in valid:
        return {'error': 'invalid outfit'}
    await update_pet_state(outfit=request.outfit)
    return {'outfit': request.outfit}
