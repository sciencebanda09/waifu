from fastapi import APIRouter
from core.database import get_pet_state, get_personality, get_skills, get_last_awareness
from core.growth import GrowthEngine, xp_for_level
from core.ollama_health import check_ollama_health

router  = APIRouter()
_growth = GrowthEngine()


@router.get("/state")
async def get_state():
    pet         = await get_pet_state()
    personality = await get_personality()
    skills      = await get_skills()
    last_aware  = await get_last_awareness()
    lp          = await _growth.get_level_progress()
    await _growth.check_evolution(lp["level"])
    ollama      = await check_ollama_health()


    from core.database import get_code_stats
    cs = await get_code_stats()

    return {
        "pet":            pet,
        "personality":    personality,
        "skills":         skills,
        "last_message":   "",
        "last_awareness": last_aware,
        "streak":         cs.get("current_streak", 0),
        "level_progress": lp,
        "ollama_ready":   ollama.get("status") == "ok",
        "ollama_error":   ollama.get("message") if ollama.get("status") != "ok" else None,
    }

from datetime import datetime as _dt

_last_activity = _dt.utcnow()

@router.post('/ping')
async def ping():
    global _last_activity
    _last_activity = _dt.utcnow()
    return {'ok': True}


from pydantic import BaseModel as _BaseModel

class _NameRequest(_BaseModel):
    name: str

@router.post('/setname')
async def set_name(request: _NameRequest):
    from core.database import set_user_pref
    await set_user_pref('user_name', request.name[:50])
    return {'name': request.name[:50]}
