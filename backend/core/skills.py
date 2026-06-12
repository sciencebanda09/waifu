import logging
from core.database import get_skills as db_get_skills, unlock_skill as db_unlock_skill, get_pet_state

logger = logging.getLogger(__name__)

SKILL_TREE = {
    "daily_roast":       {"name": "Daily Roast",         "unlock_level": 5,  "category": "commentary",  "description": "She roasts you every morning. Lovingly."},
    "code_review":       {"name": "Code Review Mode",    "unlock_level": 8,  "category": "awareness",   "description": "She judges your code in real time."},
    "dream_mode":        {"name": "Dream Sequences",     "unlock_level": 12, "category": "personality", "description": "She describes strange dreams while you work."},
    "memory_recall":     {"name": "Deep Memory",         "unlock_level": 15, "category": "memory",      "description": "She references older memories more often."},
    "mood_forecast":     {"name": "Mood Forecast",       "unlock_level": 20, "category": "personality", "description": "She tells you what mood she's heading toward."},
    "git_commentary":    {"name": "Git Commentary",      "unlock_level": 10, "category": "awareness",   "description": "She reacts to every commit message."},
    "cpu_watcher":       {"name": "CPU Watcher",         "unlock_level": 6,  "category": "awareness",   "description": "She notices when your CPU is suffering."},
    "late_night_mode":   {"name": "Late Night Mode",     "unlock_level": 7,  "category": "personality", "description": "Special late-night dialogue after midnight."},
    "streak_tracker":    {"name": "Streak Tracker",      "unlock_level": 9,  "category": "commentary",  "description": "She tracks your coding streaks obsessively."},
    "diary_reader":      {"name": "Diary Access",        "unlock_level": 18, "category": "memory",      "description": "She reads entries from her own diary aloud."},
    "shame_hall":        {"name": "Hall of Shame",       "unlock_level": 11, "category": "commentary",  "description": "She keeps a list of your worst variable names."},
    "whisperer":         {"name": "The Whisperer",       "unlock_level": 25, "category": "personality", "description": "She occasionally whispers things only you can read."},
    "possession_mode":   {"name": "Possession Mode",     "unlock_level": 35, "category": "chaos",       "description": "She takes over the chat for exactly 30 seconds."},
    "time_oracle":       {"name": "Time Oracle",         "unlock_level": 40, "category": "special",     "description": "She predicts things. Sometimes correctly."},
    "ascension_speech":  {"name": "The Speech",          "unlock_level": 50, "category": "special",     "description": "She gives a speech. Once. You won't forget it."},
}


async def seed_skills():

    from core.database import get_skills as db_get_skills
    from aiosqlite import connect as aio_connect
    from core.database import DB_PATH

    existing = {s["id"] for s in await db_get_skills()}
    async with aio_connect(DB_PATH) as db:
        for skill_id, meta in SKILL_TREE.items():
            if skill_id not in existing:
                await db.execute(
                    ,
                    (skill_id, meta["name"], meta["description"], meta["unlock_level"], meta["category"])
                )
        await db.commit()


async def get_all_skills() -> list[dict]:
    rows = await db_get_skills()
    result = []
    for r in rows:
        skill_id = r["id"]
        meta = SKILL_TREE.get(skill_id, {})
        result.append({
            **r,
            "category": meta.get("category", ""),
            "description": r.get("description") or meta.get("description", ""),
        })
    return result


async def check_and_unlock_skills() -> list[str]:

    state = await get_pet_state()
    level = state.get("level", 1)
    skills = await db_get_skills()
    newly_unlocked = []
    for s in skills:
        if not s["unlocked"] and level >= s["unlock_level"]:
            await db_unlock_skill(s["id"])
            newly_unlocked.append(s["id"])
    return newly_unlocked


async def teach_skill(skill_id: str) -> dict:

    from core.database import increment_skill_use
    if skill_id not in SKILL_TREE:
        return {"success": False, "reason": "unknown_skill"}
    await increment_skill_use(skill_id)
    return {"success": True, "skill_id": skill_id}
