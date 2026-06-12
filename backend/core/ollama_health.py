import aiohttp
import logging

OLLAMA_URL  = "http://127.0.0.1:11434"
CHAT_MODEL  = "qwen2.5:14b"
EMBED_MODEL = "nomic-embed-text"

logger = logging.getLogger(__name__)


async def check_ollama_health() -> dict:

    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
            async with session.get(f"{OLLAMA_URL}/api/tags") as resp:
                if resp.status != 200:
                    return {
                        "status": "error",
                        "reason": "ollama_unreachable",
                        "ollama": False,
                        "chat_model": False,
                        "embedding_model": False,
                        "message": f"Ollama returned HTTP {resp.status}. Is it running?",
                    }
                data = await resp.json()
    except Exception as e:
        return {
            "status": "error",
            "reason": "ollama_unreachable",
            "ollama": False,
            "chat_model": False,
            "embedding_model": False,
            "message": f"Cannot reach Ollama at {OLLAMA_URL}. Run: ollama serve",
        }

    model_names = [m.get("name", "") for m in data.get("models", [])]
    # Ollama model names may include tags like "qwen2.5:14b"
    has_chat  = any(CHAT_MODEL in n for n in model_names)
    has_embed = any(EMBED_MODEL in n for n in model_names)
    missing   = []
    if not has_chat:  missing.append(CHAT_MODEL)
    if not has_embed: missing.append(EMBED_MODEL)

    if missing:
        pull_cmds = " && ".join(f"ollama pull {m}" for m in missing)
        return {
            "status": "error",
            "reason": "missing_model",
            "required": missing,
            "ollama": True,
            "chat_model": has_chat,
            "embedding_model": has_embed,
            "message": f"Missing models. Run: {pull_cmds}",
        }

    return {
        "status": "ok",
        "ollama": True,
        "chat_model": True,
        "embedding_model": True,
    }


async def enforce_models_or_sleep() -> bool:

    result = await check_ollama_health()
    if result["status"] == "ok":
        return True
    logger.warning("=" * 60)
    logger.warning("CODEWAIFU: Models not ready — entering sleep mode")
    logger.warning(result.get("message", ""))
    logger.warning("=" * 60)
    return False
