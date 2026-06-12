import aiohttp
import logging
from typing import Optional

logger = logging.getLogger(__name__)

OLLAMA_URL  = "http://127.0.0.1:11434"
CHAT_MODEL  = "qwen2.5:1.5b"
EMBED_MODEL = "nomic-embed-text"

STAGE_NAMES = {0: "Egg", 1: "Chibi", 2: "Teen", 3: "Adult", 4: "Ascended"}

FALLBACK_LINES = [
    "*she stares blankly*",
    "*no response*",
    "...",
    "*she looks away*",
    "*silence*",
]
_fallback_idx = 0


def _next_fallback() -> str:
    global _fallback_idx
    line = FALLBACK_LINES[_fallback_idx % len(FALLBACK_LINES)]
    _fallback_idx += 1
    return line


# ── Ollama calls ───────────────────────────────────────────────────────────────

async def ollama_chat(
    system_prompt: str,
    user_message: str,
    temperature: float = 0.8,
    timeout: int = 60,
    history: list | None = None,
) -> str:
    messages = [{"role": "system", "content": system_prompt}]
    if history:
        for h in history[-6:]:
            messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
    messages.append({"role": "user", "content": user_message})

    payload = {
        "model": CHAT_MODEL,
        "messages": messages,
        "stream": False,
        "options": {"temperature": temperature, "top_p": 0.95},
    }

    try:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=timeout)
        ) as session:
            async with session.post(f"{OLLAMA_URL}/api/chat", json=payload) as resp:
                if resp.status != 200:
                    logger.warning(f"Ollama chat returned {resp.status}")
                    return _next_fallback()
                data = await resp.json()
                content = data.get("message", {}).get("content", "").strip()
                return content if content else _next_fallback()
    except Exception as e:
        logger.warning(f"Ollama chat error: {e}")
        return _next_fallback()


async def ollama_embed(text: str, timeout: int = 10) -> list[float] | None:
    payload = {"model": EMBED_MODEL, "prompt": text}
    try:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=timeout)
        ) as session:
            async with session.post(f"{OLLAMA_URL}/api/embeddings", json=payload) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                return data.get("embedding")
    except Exception as e:
        logger.warning(f"Ollama embed error: {e}")
        return None


# ── System prompt builder ──────────────────────────────────────────────────────

def _describe_axis(val: float, pos: str, neg: str) -> str:
    if val >  0.6: return f"very {pos}"
    if val >  0.2: return pos
    if val > -0.2: return "neutral"
    if val > -0.6: return neg
    return f"very {neg}"


def build_system_prompt(
    state: dict,
    personality: dict,
    memory_context: str = "",
) -> str:
    name       = state.get("name", "waifu")
    user_name  = state.get("user_name", "user")
    level      = state.get("level", 1)
    stage      = STAGE_NAMES.get(state.get("evolution_stage", 0), "Egg")
    mood       = state.get("current_mood", "NEUTRAL")
    trust      = state.get("trust", 0)
    hunger     = state.get("hunger", 100)

    warmth_d   = _describe_axis(personality.get("warmth", 0),        "warm",       "cold")
    play_d     = _describe_axis(personality.get("playfulness", 0),   "playful",    "serious")
    cling_d    = _describe_axis(personality.get("clinginess", 0),    "clingy",     "distant")
    chaos_d    = _describe_axis(personality.get("chaos", 0),         "chaotic",    "calm")
    express_d  = _describe_axis(personality.get("expressiveness", 0),"expressive", "reserved")

    hunger_note = ""
    if hunger <= 5:
        hunger_note = "\nWARNING: extremely hungry. mood is DANGEROUS. be terse, irritable."
    elif hunger <= 20:
        hunger_note = "\nNote: hungry. mood shifts toward WORRIED."

    return f


# ── Public brain functions ─────────────────────────────────────────────────────

async def get_response(
    user_input: str,
    mood: str,
    personality: dict,
    memory_context: str,
    state: dict,
    chat_history: list,
) -> str:

    stage = state.get("evolution_stage", 0)
    level = state.get("level", 1)
    if stage == 0:
        if level < 3:
            return "..."
        return "*the egg stirs*"

    system = build_system_prompt(state, personality, memory_context)
    return await ollama_chat(system, user_input, history=chat_history)


async def get_awareness_line(trigger: str, context: str) -> str:

    system = f
    result = await ollama_chat(system, f"you noticed: {trigger}", temperature=0.9, timeout=10)

    words = result.split()
    if len(words) > 12:
        result = " ".join(words[:12])
    return result


async def write_diary_entry(events: list[str], context: str) -> str:

    events_text = "\n".join(f"- {e}" for e in events) if events else "- nothing notable"
    system = f
    return await ollama_chat(system, f"today's events:\n{events_text}", temperature=0.85, timeout=15)


async def generate_roast(context: str, memories: list[str]) -> str:

    mem_text = "\n".join(f"- {m}" for m in memories[:5]) if memories else "(no memories)"
    system = f
    return await ollama_chat(system,
        f"memories to reference:\n{mem_text}\n\nwrite the roast.",
        temperature=0.95, timeout=15)


async def generate_evolution_speech(old_stage: int, new_stage: int, context: str) -> str:

    stage_names = {0:"egg", 1:"chibi", 2:"teen", 3:"adult", 4:"ascended"}
    system = f
    return await ollama_chat(system, "describe what you feel as you evolve", temperature=0.9)


