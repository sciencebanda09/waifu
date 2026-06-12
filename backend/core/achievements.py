import logging
from datetime import datetime
from core.database import DB_PATH
import aiosqlite

logger = logging.getLogger(__name__)

ACHIEVEMENTS = {
    "first_chat":    {"name": "First Words",    "desc": "Said something to her for the first time"},
    "first_feed":    {"name": "Provider",        "desc": "Fed her for the first time"},
    "commit_10":     {"name": "Committer",       "desc": "Made 10 git commits"},
    "commit_100":    {"name": "Grinder",         "desc": "Made 100 git commits"},
    "3am_commit":    {"name": "Night Owl",       "desc": "Committed code at 3am"},
    "hotfix_5":      {"name": "Bug Magnet",      "desc": "5 hotfix commits"},
    "streak_7":      {"name": "Week Warrior",    "desc": "7 day coding streak"},
    "trust_50":      {"name": "Trusted",         "desc": "Reached 50 trust"},
    "lv10":          {"name": "Growing Up",      "desc": "Reached level 10"},
    "lv50":          {"name": "Ascended",        "desc": "Reached level 50"},
    "fed_coffee_10": {"name": "Caffeinated",     "desc": "Fed her coffee 10 times"},
    "ignored_3h":    {"name": "Neglectful",      "desc": "Left her alone for 3 hours"},
    "full_warmth":   {"name": "She Loves You",   "desc": "Warmth reached maximum"},
    "full_chaos":    {"name": "Unhinged Mode",   "desc": "Chaos reached maximum"},
}


async def seed_achievements():
    async with aiosqlite.connect(DB_PATH) as db:
        for ach_id, data in ACHIEVEMENTS.items():
            await db.execute(
                "INSERT OR IGNORE INTO achievements (id, name, description) VALUES (?, ?, ?)",
                (ach_id, data["name"], data["desc"])
            )
        await db.commit()


async def unlock_achievement(ach_id: str) -> bool:

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT unlocked FROM achievements WHERE id=?", (ach_id,)) as cur:
            row = await cur.fetchone()
            if not row or row["unlocked"]:
                return False
        await db.execute(
            "UPDATE achievements SET unlocked=1, unlocked_at=? WHERE id=?",
            (datetime.utcnow().isoformat(), ach_id)
        )
        await db.commit()
        return True


async def get_achievements() -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM achievements ORDER BY unlocked DESC, id") as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def check_achievements(state: dict, stats: dict) -> list[str]:

    newly = []
    pet = state.get("pet", state)
    personality = state.get("personality", {})

    checks = {
        "commit_10":     (stats.get("total_commits", 0) >= 10),
        "commit_100":    (stats.get("total_commits", 0) >= 100),
        "hotfix_5":      (stats.get("hotfix_count", 0) >= 5),
        "streak_7":      (stats.get("current_streak", 0) >= 7),
        "trust_50":      (pet.get("trust", 0) >= 50),
        "lv10":          (pet.get("level", 0) >= 10),
        "lv50":          (pet.get("level", 0) >= 50),
        "full_warmth":   (personality.get("warmth", 0) >= 0.95),
        "full_chaos":    (personality.get("chaos", 0) >= 0.95),
    }
    for ach_id, condition in checks.items():
        if condition:
            if await unlock_achievement(ach_id):
                newly.append(ach_id)
                logger.info(f"[achievements] unlocked: {ach_id}")
    return newly
