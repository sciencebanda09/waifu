from fastapi import APIRouter
from pydantic import BaseModel
from core.skills import get_all_skills, teach_skill, check_and_unlock_skills

router = APIRouter()


class TeachRequest(BaseModel):
    skill_id: str


@router.get("/skills")
async def list_skills():
    skills = await get_all_skills()
    newly  = await check_and_unlock_skills()
    return {"skills": skills, "newly_unlocked": newly}


@router.post("/skills/teach")
async def teach(request: TeachRequest):
    from core.growth import GrowthEngine
    result = await teach_skill(request.skill_id)
    if result["success"]:
        xp = await GrowthEngine().add_xp("skill_teach")
        result["xp_gained"] = xp["xp_gained"]
    return result
