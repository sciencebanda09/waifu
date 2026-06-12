import logging
from datetime import datetime, timezone
from typing import Optional

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from core.database import (
    add_memory, store_embedding, get_all_memories_with_embeddings,
    get_recent_memories, increment_recall,
)
from core.brain import ollama_embed

logger = logging.getLogger(__name__)

STAGE_NAMES = {0: "Egg", 1: "Chibi", 2: "Teen", 3: "Adult", 4: "Ascended"}


class MemoryEngine:


    async def remember(
        self,
        type_: str,
        content: str,
        importance: int = 1,
        emotion: str = None,
    ):
        memory_id = await add_memory(type_, content, importance, emotion)
        embedding  = await ollama_embed(content)
        if embedding:
            await store_embedding(memory_id, embedding)
        return memory_id

    async def recall_semantic(self, query: str, n: int = 5) -> list[dict]:
        query_vec = await ollama_embed(query)
        if query_vec is None:
            return await self.recall_recent(n)

        all_memories = await get_all_memories_with_embeddings()
        if not all_memories:
            return []

        q = np.array(query_vec).reshape(1, -1)
        now = datetime.now(timezone.utc)
        scored = []

        for m in all_memories:
            emb = m.get("embedding")
            if not emb:
                continue
            try:
                mem_vec = np.array(emb).reshape(1, -1)
                sim = float(cosine_similarity(q, mem_vec)[0][0])
            except Exception:
                sim = 0.0


            try:
                ts_str = m.get("timestamp", "")
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                age_days = (now - ts).total_seconds() / 86400
                recency = max(0.0, 1.0 - (age_days / 30))
            except Exception:
                recency = 0.5

            importance = min(1.0, m.get("importance", 1) / 5.0)
            score = sim * 0.7 + importance * 0.2 + recency * 0.1
            scored.append((score, m))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = [m for _, m in scored[:n]]

        for m in top:
            await increment_recall(m["id"])

        return top

    async def recall_recent(self, n: int = 10) -> list[dict]:
        return await get_recent_memories(n)

    async def build_context_string(
        self,
        personality: dict,
        state: dict,
        query: str = None,
    ) -> str:
        if query:
            memories = await self.recall_semantic(query, n=5)
        else:
            memories = await self.recall_recent(n=8)

        stage_name = STAGE_NAMES.get(state.get("evolution_stage", 0), "Egg")
        lines = [
            f"LEVEL: {state.get('level',1)} | STAGE: {stage_name}",
            f"TRUST: {state.get('trust',0)}/100 | AFFECTION: {state.get('affection',0)}/100",
            f"MOOD: {state.get('current_mood','NEUTRAL')}",
            f"PERSONALITY: warm={personality.get('warmth',0):.1f} "
            f"play={personality.get('playfulness',0):.1f} "
            f"clingy={personality.get('clinginess',0):.1f} "
            f"chaos={personality.get('chaos',0):.1f}",
            f"SESSIONS: {state.get('session_count',0)}",
        ]

        if memories:
            lines.append("RELEVANT MEMORIES:")
            for m in memories:
                ts  = m.get("timestamp", "")[:10]
                typ = m.get("type", "")
                content = m.get("content", "")
                lines.append(f"  [{ts}][{typ}] {content}")
        else:
            lines.append("RELEVANT MEMORIES: (none yet)")

        return "\n".join(lines)
