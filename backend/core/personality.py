import logging
from core.database import get_personality, update_personality, get_pet_state

logger = logging.getLogger(__name__)

PERSONALITY_AXES = {
    "warmth":         {"pos": "warm",       "neg": "cold",       "range": (-1, 1)},
    "playfulness":    {"pos": "playful",     "neg": "serious",    "range": (-1, 1)},
    "clinginess":     {"pos": "clingy",      "neg": "distant",    "range": (-1, 1)},
    "chaos":          {"pos": "chaotic",     "neg": "calm",       "range": (-1, 1)},
    "expressiveness": {"pos": "expressive",  "neg": "reserved",   "range": (-1, 1)},
}

PERSONALITY_EVENTS = {
    "fed":              {"warmth": +0.02, "clinginess": +0.01},
    "petted":           {"warmth": +0.03, "expressiveness": +0.02},
    "ignored_1h":       {"warmth": -0.03, "clinginess": +0.04},
    "ignored_3h":       {"warmth": -0.05, "clinginess": +0.06},
    "late_night_code":  {"chaos": +0.02},
    "good_commit":      {"warmth": +0.01},
    "bad_var":          {"chaos": +0.01, "expressiveness": +0.02},
    "long_session":     {"clinginess": +0.02},
    "streak_milestone": {"warmth": +0.04, "expressiveness": +0.03},
    "rude_message":     {"warmth": -0.04, "clinginess": -0.02},
    "kind_message":     {"warmth": +0.04, "playfulness": +0.01},
    "cpu_spike":        {"chaos": +0.01},
    "idle_long":        {"clinginess": +0.03, "warmth": -0.01},
    "late_night":       {"chaos": +0.01, "expressiveness": +0.01},
    "hotfix":           {"chaos": +0.02, "warmth": -0.01},
    "good_code_file":   {"chaos": -0.01, "warmth": +0.01},
}

# Mood determination from personality axes + state
MOOD_RULES = [

    ("UNHINGED",   lambda p, s: p["chaos"] > 0.7),
    ("OBSESSED",   lambda p, s: p["clinginess"] > 0.6 and p["warmth"] > 0.2),
    ("DOMINANT",   lambda p, s: p["warmth"] < -0.3 and p["expressiveness"] > 0.3),
    ("COLD",       lambda p, s: p["warmth"] < -0.5),
    ("DANGEROUS",  lambda p, s: s.get("hunger", 100) <= 5),
    ("WORRIED",    lambda p, s: s.get("hunger", 100) <= 20),
    ("SOFT",       lambda p, s: p["warmth"] > 0.6 and p["expressiveness"] > 0.3),
    ("IMPRESSED",  lambda p, s: p["warmth"] > 0.4 and p["playfulness"] > 0.4),
    ("HAPPY",      lambda p, s: p["warmth"] > 0.3 and p["playfulness"] > 0.2),
    ("FOCUSED",    lambda p, s: p["chaos"] < -0.3 and p["warmth"] > -0.2),
    ("DISGUSTED",  lambda p, s: p["warmth"] < -0.2 and p["chaos"] < -0.2),
    ("BORED",      lambda p, s: abs(p["warmth"]) < 0.2 and abs(p["playfulness"]) < 0.2),
]


def _clamp(val: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, val))


async def apply_personality_event(event_type: str):
    deltas = PERSONALITY_EVENTS.get(event_type)
    if not deltas:
        logger.debug(f"No personality event for: {event_type}")
        return
    current = await get_personality()
    updates = {}
    for axis, delta in deltas.items():
        old = current.get(axis, 0.0)
        updates[axis] = _clamp(old + delta, -1.0, 1.0)
    await update_personality(**updates)


async def compute_mood(personality: dict, state: dict) -> str:
    for mood, condition in MOOD_RULES:
        try:
            if condition(personality, state):
                return mood
        except Exception:
            continue
    return "NEUTRAL"


def describe_personality(personality: dict) -> dict:
    result = {}
    for axis, meta in PERSONALITY_AXES.items():
        val = personality.get(axis, 0.0)
        if val > 0.6:
            desc = f"very {meta['pos']}"
        elif val > 0.2:
            desc = meta["pos"]
        elif val > -0.2:
            desc = "neutral"
        elif val > -0.6:
            desc = meta["neg"]
        else:
            desc = f"very {meta['neg']}"
        result[axis] = desc
    return result
