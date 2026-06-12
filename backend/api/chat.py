from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from core.database import (
    get_pet_state, update_pet_state,
    get_personality, add_chat, get_chat_history,
)
from core.memory import MemoryEngine
from core.brain import get_response, generate_roast
from core.personality import apply_personality_event, compute_mood
from core.growth import GrowthEngine
from core.skills import check_and_unlock_skills
from core.awareness import event_queue

router = APIRouter()
_mem    = MemoryEngine()
_growth = GrowthEngine()


class ChatRequest(BaseModel):
    message: str
    user_name: Optional[str] = "user"


class ChatResponse(BaseModel):
    reply: str
    mood: str
    xp_gained: int
    state_update: dict


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    msg = request.message.strip()
    if not msg:
        return ChatResponse(reply="...", mood="BORED", xp_gained=0, state_update={})

    state       = await get_pet_state()
    personality = await get_personality()
    history     = await get_chat_history(10)


    if msg.lower() in ("/diary", "diary"):
        from core.database import get_diary
        entries = await get_diary(3)
        if entries:
            text = "\n---\n".join(e["content"] for e in entries)
        else:
            text = "*the diary pages are blank*"
        await add_chat("user", msg, state.get("current_mood"))
        await add_chat("assistant", text, state.get("current_mood"))
        return ChatResponse(reply=text, mood=state.get("current_mood","BORED"), xp_gained=0, state_update={})

    if "/roast" in msg.lower():
        memories = await _mem.recall_recent(5)
        mem_texts = [m["content"] for m in memories]
        context   = await _mem.build_context_string(personality, state)
        from core.brain import generate_roast
        reply = await generate_roast(context, mem_texts)
        await add_chat("user", msg, state.get("current_mood"))
        await add_chat("assistant", reply, state.get("current_mood"))
        return ChatResponse(reply=reply, mood=state.get("current_mood","BORED"), xp_gained=0, state_update={})


    rude_words  = {"idiot","stupid","dumb","hate","shut up","useless","broken","trash"}
    kind_words  = {"thanks","love","cute","good","great","nice","beautiful","smart","amazing"}
    lower_msg   = msg.lower()
    if any(w in lower_msg for w in rude_words):
        await apply_personality_event("rude_message")
    elif any(w in lower_msg for w in kind_words):
        await apply_personality_event("kind_message")


    memory_context = await _mem.build_context_string(personality, state, query=msg)


    reply = await get_response(
        user_input=msg,
        mood=state.get("current_mood", "BORED"),
        personality=personality,
        memory_context=memory_context,
        state=state,
        chat_history=history,
    )


    await add_chat("user", msg, state.get("current_mood"))
    new_mood = await compute_mood(personality, state)
    await add_chat("assistant", reply, new_mood)


    await _mem.remember(
        "chat",
        f"user said: {msg[:100]} | replied: {reply[:100]}",
        importance=1,
        emotion=new_mood,
    )


    xp_result = await _growth.add_xp("chat_message")
    await update_pet_state(current_mood=new_mood)


    newly_unlocked = await check_and_unlock_skills()
    for skill_id in newly_unlocked:
        try:
            event_queue.put_nowait({
                "type": "skill_unlocked",
                "message": f"new skill unlocked: {skill_id.replace('_',' ')}",
                "trigger": "skill_unlock",
                "mood": new_mood,
                "xp_gained": 0,
            })
        except Exception:
            pass

    updated_state = await get_pet_state()
    return ChatResponse(
        reply=reply,
        mood=new_mood,
        xp_gained=xp_result["xp_gained"],
        state_update={
            "level": updated_state.get("level"),
            "xp": updated_state.get("xp"),
            "xp_next": updated_state.get("xp_next"),
            "leveled_up": xp_result.get("leveled_up", False),
        },
    )
