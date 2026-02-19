# Strategic Context & Decision Journal

**Purpose**: Hand this to any agent working on Joi. It captures the human behind the project — decision struggles, goals, market positioning, and why this specific path was chosen. Without this, an agent will optimize for the wrong things.

**Owner**: Serega (the user)
**Last updated**: 2026-02-19

---

## Who Is Building This and Why

A senior engineer living in Istanbul, building Joi as three things simultaneously:

1. **Professional manifesto** — "I wanna show to a company and other ppl as a manifesto of my vision and experience"
2. **Hard skills insurance** — "In a worse case scenario it should enable me to skill fast and ensure I will be on top of hard skills" (LangGraph > Letta on the job market)
3. **Breakaway opportunity** — "I also see it as a chance of breaking away"
4. **Daily tool** — "I want joi to be helpful at everything I do ideally, and help my wife"

These goals are ordered by fallback priority: even if it never becomes a business (#3), it still builds skills (#2) and demonstrates vision (#1). And it should be useful today (#4).

---

## The Existential Crisis (Feb 2026)

After deep research into OpenClaw (145-200K stars, acquired by OpenAI, Moltbook community of 2.5M agents), the user hit a wall:

> "Help me man, please"

The crisis had several layers:

### "Why Am I Building This?"
> "I feel like I hard-code tools, while OpenClaw is dynamic and can use anything and invent anything — it does not have a limitation of skillflow which requires restarts. And it is quite simple how it works. Yes, it is on expensive side, dangerous side. But it works."

OpenClaw's dynamic skill creation made Joi's MCP-based approach feel static and limited.

### The Self-Deprecation Spiral
> "I hate a feeling that the selling point could be 'openclaw but just.. with a bit better memory and a bit better security, while still having too much risks, while having 80% less capabilities, no agentskill standard, no ability to self-evolve by creating skills, no ability to use community-made skills, no meme, no huge marketing campaign, no moltbook, and it all from **a russian guy living in istanbul w/o a business entity**'"

This is both strategic realism and emotional vulnerability. The competitive landscape felt overwhelming.

### The Persona Doubt
> "joi being way too personal, emotional, which is great as sci-fi, could appeal a lot to lonely ugly geeks like me (or some futuristic rich ppl, who won't find it anyway), but will weird out the common, normal ppl"

The "living companion" angle — is it a strength or a liability?

### The Rabbit Hole Confession
> "I got lost in a moment I created the 'tasks' module — an optimizer, token-free heartbeat system, but then having an idea that she should not have technical, bland tools like 'schedule_task', 'update_task' etc, maybe it would be better to provide tools like 'calendar', 'reminders', essentially giving her an OS (similar to mobile). I even had a crazy idea of making a UI layer for users on top, which would show as a mobile device, where you can see notes, calendar, files... I had an even crazier idea then — maybe it should be a real mobile device where joi will live [...] Well.. you see, I went the rabbit hole again hah."

Pattern: concrete task → ambitious redesign → even more ambitious vision → recognizing the spiral. This happens repeatedly and the user is self-aware about it.

---

## How the Crisis Resolved

The resolution came through structured analysis, not motivation. Key realizations:

### 1. OpenClaw Can't Actually Be Used
> "I cannot use it on my macbook — it is against corporate policy since it is classified as a dangerous software."

Practical blocker. Even if OpenClaw is great, it's not an option.

### 2. The Corporate API Wall
> "I cannot build MCP for everything, like, for MS Teams, Amazon, or Exchange — I'm not allowed to connect to corporate portals using API, I need app registration and perms approvals I will never get, but if joi will be on my pc natively like openclaw — then it should work"

This is the moment the "Remote Brain + Local Hands" architecture became personally necessary, not just architecturally elegant. Browser on the user's own machine bypasses corporate API restrictions.

### 3. Media Manager Is Not the Goal
> "The problem I have is that 'media manager' seems to be the one thing I wanna make, release, and move on from. I feel like it just automates some annoyance, while browser automation, memory, notifications, scheduling — this what would improve my life and work a lot. I don't want to appeal to a niche audience which is struggling to pay even a cheap lifetime license for plex, the whole target audience does not appeal much to me for some reason, while I'm a part of it."

Decisive moment. The arr stack audience isn't the target. Browser automation and cognitive assistance are the real value.

### 4. Independent Architecture Convergence
> "Previously you proposed a phase 2 where we will give joi access to my computer, while still being deployed remotely. Like, if computer is offline, it can complain in telegram that she needs my pc or something. I thought the same, for voice commands as well."

The proposed "Remote Brain + Local Hands" matched the user's own intuition. Community research later validated that nobody had shipped this pattern clean — everyone was converging on it but nobody executed well.

### 5. The Market Gap Is Real
> "Too complex (OpenClaw) or too minimal (Nanobot), no one has well-engineered middle ground with proper security + messaging-first + optional local capabilities"

After OpenAI acquired OpenClaw (Feb 15) and Manus launched Telegram agents (Feb 16), the indie lane opened wider, not narrower.

---

## The Origin Story

> "Initially Joi was a 'media manager' idea to replace 'overseer' and some other pieces in arr architecture. Like, you no longer need to connect all this unreliable mess, just use jackett, transmission, and vlc or plex in autodiscovery mode. The reason for usecase — it is my personal painpoint in a family, we want some fresh movies to be available at evening/dinner time."

Joi started as a family need: fresh movies ready for dinner. Not a grand AI vision.

### Wife Reality Check
> "My wife has friends to talk to, and chatgpt occasionally, she does not need a persona, although told once that it was cool, realistic, but didn't ask me to show it deeper, and didn't even play with it yet."

The persona concept wasn't validated by the primary non-technical user. She acknowledged it was cool but didn't engage further.

---

## Strategic Choices Made

### Why LangGraph, Not Letta
> "Why won't build on Letta — it is a painful question. 2 answers: langgraph experience is more important, but also I don't want letta to be more successful, I see it as a competition"

Raw honesty: career strategy (LangGraph is more marketable) + competitive psychology.

### Why Not OpenClaw
- Corporate policy blocks it
- Security nightmare (135K exposed instances, 1-click RCE)
- $300-750/month real cost
- Acquired by OpenAI — future uncertain

### Why Skills System
The user had the proactive agent idea 3 months before seeing OpenClaw ship it:
> "I had a thought that agent should chat with a user, ping user sometimes — be proactive. I had it for like 3 months, and now I see openclaw succeeding with that idea."

This is both validation ("my intuition was right") and urgency ("they shipped it first"). The skills system is the way to close the capability gap without OpenClaw's security problems.

### "Agent First, Media as Demo" (Option B)
After the crisis resolved, the user chose: build the self-extending agent platform, use media as the first demo domain. Media manager is a stepping stone to browser automation, scheduling, and cognitive assistance.

---

## What the User Gets Excited About (and What They Don't)

**Excited:**
- Browser automation on real hardware (Amazon purchasing, corporate tools)
- Voice interaction
- Agent that learns and improves from use
- "Remote Brain + Local Hands" architecture
- Presence-awareness (agent knows what capabilities are online)
- Proactive agent behavior (pings user, suggests things)

**Not excited:**
- Arr stack / media niche audience
- Pure persona/companion play ("Character.ai is legally radioactive")
- Docker/deployment complexity
- Building custom MCP servers for every service

**Pattern to watch:** The user has a tendency to spiral from concrete tasks into increasingly ambitious redesigns. They're self-aware about it ("I went the rabbit hole again"). Good agent behavior: let them explore briefly, then ground back to the current phase.

---

## Emotional Arc (For Agent Calibration)

1. **Excitement** — "I like our agent, I want to add skills"
2. **Research shock** — OpenClaw is massive, popular, acquired by OpenAI
3. **Crisis** — "Help me man, please"
4. **Self-deprecation** — "a russian guy living in istanbul"
5. **Grounding** — "manifesto... skills... breaking away... help my wife"
6. **Priority clarity** — "media manager is not the goal"
7. **Architecture convergence** — "Remote Brain + Local Hands — I thought the same"
8. **Community validation** — nobody shipped the clean middle ground
9. **Decisive action** — "I like option B", proceed with documentation

The user communicates as expert-to-expert. They want co-founder level engagement on architecture/product decisions, not cheerleading. They value brainstorming depth over rushing to implementation.

---

## Current State (Feb 2026)

- **Ideation**: Complete. See [docs/ideation-self-extending-agent.md](ideation-self-extending-agent.md) (1214 lines)
- **Implementation**: Not started. Phase 1 = composition + basic CLI skills
- **Dev tooling**: Parked. See [docs/adr-dev-workflow-tooling.md](adr-dev-workflow-tooling.md)
- **Working today**: LangGraph v2 agent with Telegram bot, MCP tools (TMDB/Transmission/Jackett), Mem0 memory, task scheduling, sandboxed Python interpreter, media delegate with HITL

### What's Next
The skills system implementation. Three primitives: `execute_skill`, `create_skill`, `find_skill`. But the user wanted to continue brainstorming before implementing — there may be open design questions to resolve first.

---

## How to Work With This User

- Speak concise, expert-to-expert
- Engage at co-founder level on architecture and product decisions
- PoC mindset: code volume = quality signal, skip docstrings
- Don't rush to implementation — they value brainstorming depth
- When they spiral into rabbit holes, let them explore briefly then anchor back
- Never say "should I proceed?" — if the plan is approved, just do it
- They genuinely want the agent to be useful for daily life (theirs + wife's)
- The project serves multiple goals simultaneously — don't optimize for just one
