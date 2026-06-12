import logging
from datetime import datetime
from core.database import get_pet_state, update_pet_state
from core.personality import compute_mood, get_personality

logger = logging.getLogger(__name__)


def xp_for_level(level: int) -> int:
    return int(100 * (1.35 ** (level - 1)))


EVOLUTION_STAGES = [
    {"stage": 0, "name": "Egg",      "min_level": 0,  "sprite_prefix": "EGG"},
    {"stage": 1, "name": "Chibi",    "min_level": 6,  "sprite_prefix": "CHIBI"},
    {"stage": 2, "name": "Teen",     "min_level": 16, "sprite_prefix": "TEEN"},
    {"stage": 3, "name": "Adult",    "min_level": 31, "sprite_prefix": "ADULT"},
    {"stage": 4, "name": "Ascended", "min_level": 50, "sprite_prefix": "ASCENDED"},
]

XP_SOURCES = {
    "chat_message":  10,
    "feed":          25,
    "pet":           15,
    "commit_good":   40,
    "commit_bad":     5,
    "daily_login":   50,
    "streak_3":     100,
    "streak_7":     250,
    "skill_teach":   75,
    "long_session":  30,
    "good_code_file":20,
}

HUNGER_DECAY_RATE   = 2.0
HUNGER_FEED_AMOUNT  = 30.0
MAX_HUNGER          = 100.0
HUNGER_CRITICAL     = 20.0
HUNGER_STARVING     = 5.0

FOOD_TYPES = {
    "snack":  {"hunger": 20, "xp": 10,  "mood_bonus": None},
    "meal":   {"hunger": 40, "xp": 25,  "mood_bonus": "HAPPY"},
    "treat":  {"hunger": 15, "xp": 50,  "mood_bonus": "IMPRESSED"},
    "coffee": {"hunger":  5, "xp": 30,  "mood_bonus": "FOCUSED"},
    "commit": {"hunger": 25, "xp": 40,  "mood_bonus": None},
}

_last_hunger_decay: datetime | None = None


def _stage_for_level(level: int) -> dict:
    stage = EVOLUTION_STAGES[0]
    for s in EVOLUTION_STAGES:
        if level >= s["min_level"]:
            stage = s
    return stage


class GrowthEngine:

    async def add_xp(self, source: str, multiplier: float = 1.0) -> dict:
        base    = XP_SOURCES.get(source, 0)
        gained  = int(base * multiplier)
        if gained <= 0:
            return {"xp_gained": 0, "leveled_up": False, "new_level": 0}

        state   = await get_pet_state()
        hunger  = state.get("hunger", 100)

        if hunger <= HUNGER_STARVING:
            gained = max(1, gained // 2)

        xp      = state.get("xp", 0) + gained
        level   = state.get("level", 1)
        total   = state.get("total_xp_earned", 0) + gained
        leveled_up = False

        while xp >= xp_for_level(level):
            xp -= xp_for_level(level)
            level += 1
            leveled_up = True

        xp_next = xp_for_level(level)
        new_stage = _stage_for_level(level)["stage"]

        await update_pet_state(
            xp=xp, level=level, xp_next=xp_next,
            total_xp_earned=total, evolution_stage=new_stage,
        )

        return {"xp_gained": gained, "leveled_up": leveled_up, "new_level": level}

    async def feed(self, food_type: str) -> dict:
        food = FOOD_TYPES.get(food_type, FOOD_TYPES["snack"])
        state = await get_pet_state()
        old_hunger = state.get("hunger", 100)
        new_hunger = min(MAX_HUNGER, old_hunger + food["hunger"])

        personality = await get_personality()
        mood = food.get("mood_bonus") or await compute_mood(personality, {**state, "hunger": new_hunger})

        await update_pet_state(
            hunger=new_hunger,
            current_mood=mood,
            last_fed=datetime.utcnow().isoformat(),
        )

        xp_result = await self.add_xp("feed")
        return {
            "hunger_before": round(old_hunger, 1),
            "hunger_after":  round(new_hunger, 1),
            "xp_gained":     xp_result["xp_gained"],
            "mood":          mood,
            "food_type":     food_type,
            "message":       f"*eats the {food_type} happily*" if new_hunger > 50 else f"*devours the {food_type}*",
        }

    async def decay_hunger(self):

        global _last_hunger_decay
        now = datetime.utcnow()
        if _last_hunger_decay is None:
            _last_hunger_decay = now
            return

        elapsed_hours = (now - _last_hunger_decay).total_seconds() / 3600
        if elapsed_hours < 0.01:
            return

        _last_hunger_decay = now
        decay = HUNGER_DECAY_RATE * elapsed_hours

        state = await get_pet_state()
        old   = state.get("hunger", 100)
        new   = max(0.0, old - decay)

        updates: dict = {"hunger": new}


        personality = await get_personality()
        if new <= HUNGER_STARVING:
            updates["current_mood"] = "DANGEROUS"
        elif new <= HUNGER_CRITICAL:
            updates["current_mood"] = "WORRIED"
        else:
            mood = await compute_mood(personality, {**state, "hunger": new})
            updates["current_mood"] = mood

        await update_pet_state(**updates)
        return new

    async def check_evolution(self, level: int) -> bool:

        state = await get_pet_state()
        old_stage = state.get("evolution_stage", 0)
        new_stage = _stage_for_level(level)["stage"]
        if new_stage > old_stage:
            await update_pet_state(evolution_stage=new_stage)
            return True
        return False

    async def get_level_progress(self) -> dict:
        state = await get_pet_state()
        level = state.get("level", 1)
        xp    = state.get("xp", 0)
        xp_next = xp_for_level(level)
        return {
            "level":   level,
            "xp":      xp,
            "xp_next": xp_next,
            "percent": round((xp / xp_next) * 100, 1) if xp_next else 0,
            "stage":   _stage_for_level(level),
        }

    async def update_trust_affection(self, trust_delta: int = 0, aff_delta: int = 0):
        state = await get_pet_state()
        new_trust = max(0, min(100, state.get("trust", 0) + trust_delta))
        new_aff   = max(0, min(100, state.get("affection", 0) + aff_delta))
        await update_pet_state(trust=new_trust, affection=new_aff)

    async def daily_decay(self):

        state = await get_pet_state()
        last_seen_str = state.get("last_seen", "")
        try:
            last_seen = datetime.fromisoformat(last_seen_str)
            days = (datetime.utcnow() - last_seen).days
        except Exception:
            days = 0

        if days >= 1:
            await self.update_trust_affection(
                trust_delta  = -days,
                aff_delta    = -days * 3,
            )
