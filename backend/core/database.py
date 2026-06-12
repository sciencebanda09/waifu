import aiosqlite
import json
import os
from datetime import datetime, date

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "codewaifu.db")
DB_PATH = os.path.abspath(DB_PATH)

SCHEMA =

SEED_PET = "INSERT OR IGNORE INTO pet_state (id) VALUES (1);"
SEED_PERSONALITY = "INSERT OR IGNORE INTO personality (id) VALUES (1);"
SEED_CODE_STATS  = "INSERT OR IGNORE INTO code_stats (id) VALUES (1);"


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        await db.execute(SEED_PET)
        await db.execute(SEED_PERSONALITY)
        await db.execute(SEED_CODE_STATS)
        await db.commit()


async def _conn():
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    return db


# ── pet_state ──────────────────────────────────────────────────────────────────

async def get_pet_state() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM pet_state WHERE id=1") as cur:
            row = await cur.fetchone()
            return dict(row) if row else {}


async def update_pet_state(**kwargs):
    if not kwargs:
        return
    kwargs["last_seen"] = datetime.utcnow().isoformat()
    cols = ", ".join(f"{k}=?" for k in kwargs)
    vals = list(kwargs.values())
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE pet_state SET {cols} WHERE id=1", vals)
        await db.commit()


# ── personality ────────────────────────────────────────────────────────────────

async def get_personality() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM personality WHERE id=1") as cur:
            row = await cur.fetchone()
            return dict(row) if row else {}


async def update_personality(**kwargs):
    if not kwargs:
        return
    kwargs["updated_at"] = datetime.utcnow().isoformat()
    cols = ", ".join(f"{k}=?" for k in kwargs)
    vals = list(kwargs.values())
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE personality SET {cols} WHERE id=1", vals)
        await db.commit()


# ── memories ───────────────────────────────────────────────────────────────────

async def add_memory(type_: str, content: str, importance: int = 1,
                     emotion: str = None) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO memories (type, content, importance, emotion) VALUES (?,?,?,?)",
            (type_, content, importance, emotion)
        )
        await db.commit()
        return cur.lastrowid


async def store_embedding(memory_id: int, embedding: list):
    blob = json.dumps(embedding).encode()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO memory_embeddings (memory_id, embedding) VALUES (?,?)",
            (memory_id, blob)
        )
        await db.commit()


async def get_all_memories_with_embeddings() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute() as cur:
            rows = await cur.fetchall()
            result = []
            for r in rows:
                d = dict(r)
                if d.get("embedding"):
                    d["embedding"] = json.loads(d["embedding"])
                result.append(d)
            return result


async def get_recent_memories(n: int = 10) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM memories ORDER BY timestamp DESC LIMIT ?", (n,)
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def increment_recall(memory_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE memories SET recalled_count=recalled_count+1 WHERE id=?", (memory_id,)
        )
        await db.commit()


# ── chat_history ───────────────────────────────────────────────────────────────

async def add_chat(role: str, content: str, mood: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO chat_history (role, content, mood) VALUES (?,?,?)",
            (role, content, mood)
        )
        await db.commit()


async def get_chat_history(n: int = 20) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM chat_history ORDER BY timestamp DESC LIMIT ?", (n,)
        ) as cur:
            rows = await cur.fetchall()
            return list(reversed([dict(r) for r in rows]))


# ── skills ─────────────────────────────────────────────────────────────────────

async def get_skills() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM skills ORDER BY unlock_level") as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def unlock_skill(skill_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE skills SET unlocked=1 WHERE id=?", (skill_id,)
        )
        await db.commit()


async def increment_skill_use(skill_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE skills SET times_used=times_used+1 WHERE id=?", (skill_id,)
        )
        await db.commit()


# ── diary ──────────────────────────────────────────────────────────────────────

async def add_diary_entry(content: str, mood: str = None, highlights: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO diary (content, mood, session_highlights) VALUES (?,?,?)",
            (content, mood, highlights)
        )
        await db.commit()


async def get_diary(n: int = 7) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM diary ORDER BY date DESC, id DESC LIMIT ?", (n,)
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


# ── awareness_log ──────────────────────────────────────────────────────────────

async def log_awareness(trigger: str, message: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO awareness_log (trigger, message) VALUES (?,?)",
            (trigger, message)
        )
        await db.commit()


async def get_last_awareness() -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT message FROM awareness_log ORDER BY timestamp DESC LIMIT 1"
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else ""


# ── code_stats ─────────────────────────────────────────────────────────────────

async def get_code_stats() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM code_stats WHERE id=1") as cur:
            row = await cur.fetchone()
            if not row:
                return {}
            d = dict(row)
            for field in ("languages_seen", "hall_of_shame", "hall_of_fame"):
                try:
                    d[field] = json.loads(d.get(field) or "[]")
                except Exception:
                    d[field] = []
            return d


async def update_code_stats(**kwargs):
    if not kwargs:
        return

    for field in ("languages_seen", "hall_of_shame", "hall_of_fame"):
        if field in kwargs and isinstance(kwargs[field], list):
            kwargs[field] = json.dumps(kwargs[field])
    cols = ", ".join(f"{k}=?" for k in kwargs)
    vals = list(kwargs.values())
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE code_stats SET {cols} WHERE id=1", vals)
        await db.commit()


async def get_user_prefs() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM user_prefs WHERE id=1") as cur:
            row = await cur.fetchone()
            return dict(row) if row else {"user_name": "user", "outfit": "seifuku2", "hair_style": "long", "hair_color": "brown"}

async def set_user_pref(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO user_prefs (id) VALUES (1)")
        await db.execute(f"UPDATE user_prefs SET {key} = ? WHERE id=1", (value,))
        await db.commit()
