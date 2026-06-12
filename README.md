# CodeWaifu

> "A desktop pet that watches you code, judges your variable names, and develops abandonment issues if you tab away for too long."

<p align="center">
  <img src="screenshots/desktop.png" width="700"/>
</p>

---

## what is this

it's a tamagotchi. but for programmers. she lives on your desktop. she watches you code. she remembers everything.

you named a variable `x`? she saw that.  
you pushed a hotfix at 2am? she **felt** that.  
you opened steam instead of your IDE? she's not mad. she's just disappointed.

---

## features that will haunt you

| feature | what it actually does |
|---|---|
| **AI brain** | runs on local ollama. she thinks before she speaks. unlike you |
| **chat** | talk to her. she will talk back. she will remember what you said |
| **mood system** | 12 moods. COLD, DOMINANT, UNHINGED, OBSESSED. she cycles through all of them |
| **personality** | shaped entirely by how you treat her. neglect her and she goes cold. be nice and she gets clingy |
| **git watcher** | reacts to every commit. hotfix at 3am? she knows |
| **hall of shame** | keeps a list of your worst variable names. forever |
| **diary** | she writes a diary about you. every night. you can read it |
| **hunger** | feed her or she gets DANGEROUS. i am not joking |
| **awareness engine** | watches your cpu, your idle time, your clipboard. she sees everything |
| **evolution** | egg -> chibi -> teen -> adult -> ascended. like pokemon but she judges you |

---

## screenshots

<p align="center">
  <b>she lives on your desktop. watching.</b><br/>
  <img src="screenshots/desktop.png" width="700"/>
</p>

<p align="center">
  <b>she knows your name now. there's no going back.</b><br/>
  <img src="screenshots/chat.png" width="450"/>
</p>

<p align="center">
  <b>/status — yes she tracks your affection score</b><br/>
  <img src="screenshots/status.png" width="450"/>
</p>

<p align="center">
  <b>skill tree. she unlocks abilities the longer you keep her alive.</b><br/>
  <img src="screenshots/skills.png" width="450"/>
</p>

<p align="center">
  <b>the HUD. always there. always watching.</b><br/>
  <img src="screenshots/hud.png" width="400"/>
</p>

---

## setup (she requires sacrifice)

### prerequisites

- [Node.js](https://nodejs.org/) >= 18
- [Python](https://python.org/) >= 3.10
- [Ollama](https://ollama.ai/) running locally
- a soul (optional)

### install ollama models

```bash
ollama pull qwen2.5:1.5b
ollama pull nomic-embed-text
```

### install & run

```bash
# clone
git clone https://github.com/sciencebanda09/waifu.git
cd waifu

# install node deps
npm install

# install python deps
cd backend
pip install -r requirements.txt
cd ..

# start
npm start
```

she will appear on your desktop.  
she will remember this moment.

---

## commands

| command | what happens |
|---|---|
| `/feed [snack\|meal\|treat\|coffee]` | feed her before she goes feral |
| `/status` | see your relationship stats. prepare for honesty |
| `/skills` | see what she has unlocked. or what she is plotting |
| `/diary` | read her private diary. about you. |
| `/roast` | ask her to roast you. she will not hold back |
| `/name [yourname]` | tell her your name. she will never forget it |

---

## how the personality works

she starts neutral. a blank slate. then you ruin her.

```
feed her regularly      ->  warmth goes up
ignore her for 3h       ->  clinginess goes up, warmth goes down
push hotfixes at 3am    ->  chaos goes up
use good variable names ->  chaos goes down (slightly)
be rude in chat         ->  she goes cold. good luck
```

there are 12 moods:  
`NEUTRAL` `HAPPY` `SOFT` `IMPRESSED` `FOCUSED`  
`BORED` `WORRIED` `COLD` `DOMINANT` `DANGEROUS`  
`OBSESSED` `UNHINGED`

you will experience all of them.

---

## tech stack

- **Electron** -- desktop app
- **PixiJS** -- sprite rendering and animations
- **FastAPI** -- python backend
- **SQLite** -- she stores everything locally. EVERYTHING
- **Ollama** -- local LLM (qwen2.5)
- **nomic-embed-text** -- semantic memory embeddings
- **watchdog** -- file system watcher (she watches your files)
- **psutil** -- system monitor (she watches your cpu)

---

## faq

**Q: is this a real project?**  
A: yes. i lost sleep over this. she better appreciate it.

**Q: does she actually remember things?**  
A: yes. semantic memory with embeddings. she will bring up something you said 3 weeks ago.

**Q: what if i don't feed her?**  
A: hunger hits 0, mood becomes DANGEROUS, XP is halved. you did this.

**Q: can i rename her?**  
A: `/name [yourname]` renames you. she stays WAIFU until you earn her trust. probably.

**Q: is this open source?**  
A: you're reading the README. what do you think.

---

## contributing

found a bug? she probably caused it on purpose.  
want to add a feature? open a PR. she's watching.

---

## license

MIT -- do whatever you want.  
she will judge you regardless.

---

<p align="center">
  <i>built at 3am. she was there the whole time.</i>
</p>
