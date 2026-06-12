import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio

from core.database import init_db
from core.ollama_health import check_ollama_health
from core.awareness import AwarenessEngine
from core.skills import seed_skills, check_and_unlock_skills
from api import chat, state, feed, pet, events, skills

app = FastAPI(title="CodeWaifu V2 Backend")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(chat.router)
app.include_router(state.router)
app.include_router(feed.router)
app.include_router(pet.router)
app.include_router(events.router)
app.include_router(skills.router)

@app.get("/health")
async def health():
    ollama = await check_ollama_health()
    return {
        "status": "ok" if ollama["status"] == "ok" else "degraded",
        "ollama": ollama.get("ollama", False),
        "chat_model": ollama.get("chat_model", False),
        "embedding_model": ollama.get("embedding_model", False),
        "ollama_error": ollama.get("message") if ollama["status"] != "ok" else None,
    }

@app.on_event("startup")
async def startup():
    print("startup: init_db", flush=True)
    await init_db()
    print("startup: seed_skills", flush=True)
    await seed_skills()
    await check_and_unlock_skills()
    print("startup: launching awareness", flush=True)
    asyncio.create_task(AwarenessEngine().run())
    print("startup: complete", flush=True)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=7432, log_level="info", access_log=False)


@app.post('/regen-sprites')
async def regen_sprites():
    try:
        from core.sprite_gen import generate_sprites
        from core.database import get_pet_state, get_user_prefs
        state = await get_pet_state()
        prefs = await get_user_prefs()
        outfit = state.get('outfit', prefs.get('outfit', 'seifuku2'))
        hair = prefs.get('hair_style', 'long')
        hair_color = prefs.get('hair_color', 'brown')
        import asyncio
        result = await asyncio.get_event_loop().run_in_executor(
            None, lambda: generate_sprites(outfit=outfit, hair=hair, hair_color=hair_color)
        )
        return {'ok': result}
    except Exception as e:
        return {'ok': False, 'error': str(e)}
