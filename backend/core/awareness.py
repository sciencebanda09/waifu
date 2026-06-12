import asyncio
import logging
import os
import re
import subprocess
from datetime import datetime, timedelta
from typing import Optional

import psutil
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from core.database import (
    get_pet_state, update_pet_state, log_awareness, get_code_stats, update_code_stats
)
from core.growth import GrowthEngine
from core.personality import apply_personality_event
from core.brain import get_awareness_line

logger = logging.getLogger(__name__)

# Global SSE event queue — populated here, read by events.py
event_queue: asyncio.Queue = asyncio.Queue(maxsize=100)

_growth = GrowthEngine()

HOME_DIR = os.path.expanduser("~")
WATCH_DIRS = [HOME_DIR]

# State tracking
_last_git_commit: str | None = None
_session_start: datetime = datetime.utcnow()
_cpu_spike_cooldown: datetime = datetime.utcnow()
_last_idle_check: datetime = datetime.utcnow()
_last_day_checked: str = ""


class AwarenessEngine:

    def __init__(self):
        self._file_handler = _CodeFileHandler(self)
        self._observer: Optional[Observer] = None

    async def run(self):
        logger.info("[awareness] engine started")
        try:
            await asyncio.gather(
                self.hunger_decay_loop(),
                self.idle_watcher(),
                self.time_of_day_watcher(),
                self.git_watcher(),
                self.cpu_watcher(),
                self.streak_checker(),
                self.diary_writer(),
                self.daily_decay_loop(),
                self._file_watcher_loop(),
                self.daily_roast_scheduler(),
                self.app_focus_watcher(),
                self.clipboard_watcher(),
            )
        except Exception as e:
            logger.error(f"[awareness] fatal: {e}")

    async def push_event(self, trigger: str, message: str = None, event_type: str = "awareness",
                         mood: str = None, xp_gained: int = 0):
        if message is None:
            state = await get_pet_state()
            context = f"pet is level {state.get('level',1)}, mood {state.get('current_mood','BORED')}"
            try:
                message = await get_awareness_line(trigger, context)
            except Exception:
                message = f"*notices {trigger}*"

        await log_awareness(trigger, message)
        evt = {
            "type":      event_type,
            "message":   message,
            "trigger":   trigger,
            "mood":      mood,
            "xp_gained": xp_gained,
            "timestamp": datetime.utcnow().isoformat(),
        }
        try:
            event_queue.put_nowait(evt)
        except asyncio.QueueFull:
            pass



    async def hunger_decay_loop(self):
        while True:
            try:
                new_hunger = await _growth.decay_hunger()
                if new_hunger is not None:
                    state = await get_pet_state()
                    if new_hunger <= 5:
                        await self.push_event("hunger_critical", "*she is starving*",
                                              event_type="hunger_warning", mood="DANGEROUS")
                    elif new_hunger <= 20:
                        await self.push_event("hunger_low", "feed her",
                                              event_type="hunger_warning", mood="WORRIED")
            except Exception as e:
                logger.debug(f"hunger decay error: {e}")
            await asyncio.sleep(300)



    async def idle_watcher(self):
        global _last_idle_check
        idle_warned_1h = False
        idle_warned_3h = False
        while True:
            await asyncio.sleep(60)
            now = datetime.utcnow()
            from api.state import _last_activity as last_activity
            idle_minutes = (now - last_activity).total_seconds() / 60

            if idle_minutes >= 180 and not idle_warned_3h:
                idle_warned_3h = True
                idle_warned_1h = True
                await apply_personality_event("ignored_3h")
                await self.push_event("idle_3h", event_type="awareness")

            elif idle_minutes >= 60 and not idle_warned_1h:
                idle_warned_1h = True
                await apply_personality_event("ignored_1h")
                await self.push_event("idle_1h", event_type="awareness")


            if idle_minutes < 5:
                idle_warned_1h = False
                idle_warned_3h = False



    async def time_of_day_watcher(self):
        announced_today: set = set()
        while True:
            await asyncio.sleep(60)
            now = datetime.now()
            h   = now.hour
            key = (now.date().isoformat(), h)

            if h == 9 and key not in announced_today:
                announced_today.add(key)
                await self.push_event("morning", event_type="awareness")

            elif h == 23 and key not in announced_today:
                announced_today.add(key)
                await apply_personality_event("late_night")
                await self.push_event("late_night_coding", event_type="awareness")

            elif h == 3 and key not in announced_today:
                announced_today.add(key)
                await apply_personality_event("late_night_code")
                await self.push_event("3am_coding", "still awake at 3am. she's watching.",
                                      event_type="awareness")



    async def git_watcher(self):
        global _last_git_commit
        while True:
            await asyncio.sleep(30)
            try:
                result = subprocess.run(
                    ["git", "log", "-1", "--pretty=%H|%s|%ai"],
                    capture_output=True, text=True, timeout=5,
                    cwd=HOME_DIR,
                )
                if result.returncode != 0:
                    continue
                line = result.stdout.strip()
                if not line:
                    continue
                parts = line.split("|", 2)
                if len(parts) < 2:
                    continue
                commit_hash, commit_msg = parts[0], parts[1]
                if commit_hash == _last_git_commit:
                    continue
                _last_git_commit = commit_hash

                stats = await get_code_stats()
                total = stats.get("total_commits", 0) + 1
                await update_code_stats(total_commits=total, last_commit_msg=commit_msg)

                is_hotfix = any(w in commit_msg.lower() for w in ["fix","hotfix","bug","patch","urgent"])
                is_late   = datetime.now().hour >= 23 or datetime.now().hour <= 4

                if is_hotfix:
                    hotfixes = stats.get("hotfix_count", 0) + 1
                    await update_code_stats(hotfix_count=hotfixes)
                    await apply_personality_event("hotfix")
                    await self.push_event(f"hotfix: {commit_msg}", event_type="awareness")
                elif is_late:
                    late = stats.get("late_night_commits", 0) + 1
                    await update_code_stats(late_night_commits=late)
                    await apply_personality_event("late_night_code")
                    await self.push_event(f"commit at {datetime.now().hour}:00", event_type="awareness")
                else:
                    await apply_personality_event("good_commit")
                    xp = await _growth.add_xp("commit_good")
                    await self.push_event(
                        f"commit: {commit_msg[:40]}",
                        event_type="awareness",
                        xp_gained=xp["xp_gained"],
                    )

                if xp := await _growth.add_xp("commit_good" if not is_hotfix else "commit_bad"):
                    if xp.get("leveled_up"):
                        await self.push_event("level_up", event_type="level_up")

            except Exception as e:
                logger.debug(f"git watcher: {e}")



    async def cpu_watcher(self):
        global _cpu_spike_cooldown
        while True:
            await asyncio.sleep(15)
            try:
                cpu = psutil.cpu_percent(interval=1)
                if cpu > 85 and datetime.utcnow() > _cpu_spike_cooldown:
                    _cpu_spike_cooldown = datetime.utcnow() + timedelta(minutes=5)
                    await apply_personality_event("cpu_spike")
                    await self.push_event(f"cpu_spike_{int(cpu)}pct",
                                          f"cpu at {int(cpu)}%. she feels it.",
                                          event_type="awareness")
            except Exception:
                pass



    async def streak_checker(self):
        global _last_day_checked
        while True:
            await asyncio.sleep(3600)
            today = datetime.now().date().isoformat()
            if today == _last_day_checked:
                continue
            _last_day_checked = today

            try:
                stats = await get_code_stats()
                streak = stats.get("current_streak", 0)

                total = stats.get("total_commits", 0)
                if total > 0:
                    streak += 1
                    longest = max(streak, stats.get("longest_streak", 0))
                    await update_code_stats(current_streak=streak, longest_streak=longest)
                    if streak in (3, 7, 14, 30):
                        await apply_personality_event("streak_milestone")
                        await self.push_event(
                            f"streak_{streak}",
                            f"{streak} day streak. she approves.",
                            event_type="awareness",
                            xp_gained=(await _growth.add_xp(f"streak_{streak}" if streak in (3,7) else "streak_3"))["xp_gained"],
                        )
            except Exception as e:
                logger.debug(f"streak checker: {e}")



    async def diary_writer(self):

        while True:
            now = datetime.now()

            tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=5, second=0)
            wait_secs = (tomorrow - now).total_seconds()
            await asyncio.sleep(wait_secs)
            try:
                from core.database import add_diary_entry, get_recent_memories
                from core.brain import write_diary_entry
                from core.memory import MemoryEngine

                state = await get_pet_state()
                recent = await get_recent_memories(10)
                events_text = [m["content"] for m in recent]
                mem = MemoryEngine()
                context = await mem.build_context_string({}, state)
                entry = await write_diary_entry(events_text, context)
                await add_diary_entry(entry, state.get("current_mood"), "")
                await self.push_event("diary_written", event_type="diary_written")
            except Exception as e:
                logger.debug(f"diary writer: {e}")



    async def daily_decay_loop(self):
        while True:
            await asyncio.sleep(3600)
            try:
                await _growth.daily_decay()
            except Exception:
                pass



    async def _file_watcher_loop(self):
        loop = asyncio.get_event_loop()
        self._observer = Observer()
        for d in WATCH_DIRS:
            if os.path.isdir(d):
                self._observer.schedule(self._file_handler, d, recursive=True)
        self._observer.start()
        try:
            while True:
                await asyncio.sleep(1)
        except Exception:
            self._observer.stop()
        self._observer.join()



    def _analyze_code_quality(self, filepath: str) -> dict:
        bad_vars = 0
        good_patterns = 0
        score = 50
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            return {"bad_vars": 0, "good_patterns": 0, "score": 50}

        ext = os.path.splitext(filepath)[1].lower()
        if ext not in (".py", ".js", ".ts", ".jsx", ".tsx"):
            return {"bad_vars": 0, "good_patterns": 0, "score": 50}


        bad_var_pattern = re.compile(r'\b([a-wz])\s*=\s*(?!>)')
        bad_vars += len(bad_var_pattern.findall(content))


        if re.search(r'except.*:\s*\n\s*pass', content):
            bad_vars += 2


        bad_vars += len(re.findall(r'#\s*TODO', content, re.IGNORECASE))


        if ext == ".py":
            bad_vars += len(re.findall(r'\bprint\(', content))


        if ext in (".js", ".ts", ".jsx", ".tsx"):
            bad_vars += len(re.findall(r'console\.log\(', content))


        for line in content.split("\n"):
            indent = len(line) - len(line.lstrip())
            if indent >= 20:
                bad_vars += 1


        if re.search(r'def test_|it\(|describe\(', content):
            good_patterns += 2
        if re.search(r'', content):
            good_patterns += 1
        if re.search(r'type\s+\w+\s*=|:\s*(str|int|float|bool|list|dict)\b', content):
            good_patterns += 1

        score = max(0, min(100, 70 - bad_vars * 5 + good_patterns * 10))
        return {"bad_vars": bad_vars, "good_patterns": good_patterns, "score": score}




    async def app_focus_watcher(self):
        last_app = None
        app_times = {}

        while True:
            await asyncio.sleep(30)
            try:
                focus_apps = {
                    "Code.exe": "vscode", "code": "vscode",
                    "chrome.exe": "browser", "firefox.exe": "browser",
                    "Cursor.exe": "cursor",
                    "python.exe": "python", "node.exe": "node",
                    "slack.exe": "slack", "discord.exe": "discord",
                    "Steam.exe": "gaming", "EpicGamesLauncher.exe": "gaming",
                }
                running = {p.name() for p in psutil.process_iter(["name"])}
                detected = None
                for proc_name, app_label in focus_apps.items():
                    if proc_name in running:
                        detected = app_label
                        break

                if detected and detected != last_app:
                    last_app = detected
                    app_times[detected] = app_times.get(detected, 0) + 0.5

                    if detected == "gaming":
                        await apply_personality_event("ignored_1h")
                        await self.push_event("user_gaming", "gaming instead of coding. she noticed.", event_type="awareness")
                    elif detected == "vscode":
                        await self.push_event("vscode_opened", event_type="awareness")
                    elif detected == "browser" and app_times.get("browser", 0) > 30:
                        await self.push_event("too_much_browser", event_type="awareness")
            except Exception as e:
                logger.debug(f"app focus watcher: {e}")



    async def clipboard_watcher(self):
        last_clip = ""
        while True:
            await asyncio.sleep(10)
            try:
                result = subprocess.run(
                    ["powershell", "-command", "Get-Clipboard"],
                    capture_output=True, text=True, timeout=3
                )
                clip = result.stdout.strip()[:200]
                if clip and clip != last_clip and len(clip) > 20:
                    last_clip = clip
                    code_signals = ["def ", "function ", "const ", "import ", "class ", "() =>", "async "]
                    if any(s in clip for s in code_signals):
                        await apply_personality_event("good_code_file")
                        await self.push_event("code_copied", event_type="awareness")
                    elif "stackoverflow.com" in clip or "github.com" in clip:
                        await self.push_event("copying_from_stackoverflow",
                            "*she saw that.*", event_type="awareness")
            except Exception:
                pass



    async def daily_roast_scheduler(self):
        while True:
            now = datetime.now()
            next_9am = now.replace(hour=9, minute=0, second=0, microsecond=0)
            if now.hour >= 9:
                next_9am += timedelta(days=1)
            await asyncio.sleep((next_9am - now).total_seconds())

            try:
                from core.database import get_skills
                skills = await get_skills()
                roast_unlocked = any(s["id"] == "daily_roast" and s["unlocked"] for s in skills)
                if roast_unlocked:
                    from core.memory import MemoryEngine
                    from core.brain import generate_roast
                    mem = MemoryEngine()
                    state = await get_pet_state()
                    memories = await mem.recall_recent(5)
                    mem_texts = [m["content"] for m in memories]
                    context = await mem.build_context_string({}, state)
                    roast = await generate_roast(context, mem_texts)
                    await self.push_event("daily_roast", roast, event_type="awareness")
            except Exception as e:
                logger.debug(f"daily roast: {e}")

class _CodeFileHandler(FileSystemEventHandler):
    SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}
    CODE_EXTS = {".py", ".js", ".ts", ".jsx", ".tsx", ".rs", ".go", ".java", ".cpp", ".c"}

    def __init__(self, engine: AwarenessEngine):
        self._engine = engine
        self._loop: asyncio.AbstractEventLoop | None = None

    def _get_loop(self):
        if self._loop is None:
            try:
                self._loop = asyncio.get_event_loop()
            except RuntimeError:
                pass
        return self._loop

    def on_modified(self, event):
        if event.is_directory:
            return
        path = event.src_path
        for skip in self.SKIP_DIRS:
            if f"/{skip}/" in path or path.endswith(f"/{skip}"):
                return
        ext = os.path.splitext(path)[1].lower()
        if ext not in self.CODE_EXTS:
            return

        analysis = self._engine._analyze_code_quality(path)
        loop = self._get_loop()
        if loop and loop.is_running():
            filename = os.path.basename(path)
            if analysis["bad_vars"] > 3:
                asyncio.run_coroutine_threadsafe(
                    _handle_bad_code(self._engine, filename, analysis), loop
                )
            elif analysis["good_patterns"] >= 2:
                asyncio.run_coroutine_threadsafe(
                    _handle_good_code(self._engine, filename, analysis), loop
                )


async def _handle_bad_code(engine: AwarenessEngine, filename: str, analysis: dict):
    stats = await get_code_stats()
    bad_count = stats.get("bad_var_count", 0) + analysis["bad_vars"]
    shame = stats.get("hall_of_shame") or []
    if isinstance(shame, str):
        import json
        shame = json.loads(shame) if shame else []
    if filename not in shame and len(shame) < 20:
        shame.append(filename)
    await update_code_stats(bad_var_count=bad_count, hall_of_shame=shame)
    await apply_personality_event("bad_var")
    await engine.push_event(
        f"bad_code:{filename}",
        f"what is this. {filename}. seriously.",
        event_type="awareness",
    )


async def _handle_good_code(engine: AwarenessEngine, filename: str, analysis: dict):
    stats = await get_code_stats()
    good_count = stats.get("good_code_count", 0) + 1
    fame = stats.get("hall_of_fame") or []
    if isinstance(fame, str):
        import json
        fame = json.loads(fame) if fame else []
    if filename not in fame and len(fame) < 20:
        fame.append(filename)
    await update_code_stats(good_code_count=good_count, hall_of_fame=fame)
    await apply_personality_event("good_code_file")
    xp = await _growth.add_xp("good_code_file")
    await engine.push_event(
        f"good_code:{filename}",
        event_type="awareness",
        xp_gained=xp["xp_gained"],
    )
