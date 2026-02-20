# Self-Extending Agent: Ideation Map

## Vision
An AI agent (Joi) that extends its own capabilities through experience, using the OS as its workshop. Not just a chatbot with tools — a system that compounds knowledge over time. Users get new capabilities through USE, not through developer release cycles. The difference between a contractor who forgets everything between jobs and an employee who builds institutional knowledge.

**The OS is the agent's workshop.** Instead of engineering custom tools for every capability, the agent leverages what's already installed — curl, python, ffmpeg, sqlite3 — thousands of built-in capabilities from training data, zero extra engineering. The agent's superpower is discovering which existing tools solve its problems most efficiently.

This is the difference between a calculator and a computer: fixed-function vs. general-purpose. Traditional agents are locked into whatever tools developers designed. An agent that can access the OS and create its own skills? That's not incremental — it's a revolution. But a secure, sane one.

---

## Core Tension
**Capability vs. Safety**: Full OS access = infinite capability but infinite risk. The fundamental design challenge is resolving this without sacrificing either side.

This isn't a technical problem to solve — it's a **design tension to resolve**. The way you resolve design tensions is by finding the right abstraction that makes the contradiction dissolve.

---

## Three-Dimensional Framework

Three axes for reasoning about where to position a self-extending agent:

1. **Capability axis** — What can the agent DO?
   `Use existing tools → Compose tools → Discover new tools → Install tools → Modify environment`

2. **Safety axis** — How do we ensure it's not destructive?
   `Developer-defined → Allowlisted → Sandboxed → HITL → Unrestricted`

3. **Learning axis** — How does knowledge persist?
   `No persistence → Session memory → Prompt-based skills → Executable skills → Self-modifying code`

The sweet spot isn't at any extreme — it's at the intersection where you get maximum useful capability with structural (not just procedural) safety. Each design decision is a point in this 3D space.

---

## Key Insights (Validated)

### 1. Skills = Compositions of Trusted Primitives
- Skills should chain existing safe tools, not execute arbitrary code
- When a skill CAN'T be composed from existing tools → signal to add a new primitive (human decision)
- The agent identifies its own capability gaps and proposes extensions
- **Source**: Our reasoning, validated by AgentSkills spec's `allowed-tools` field

### 2. CLI Tools Are the World's Largest Skill Library
- `yt-dlp`, `ffmpeg`, `jq`, `vercel` — thousands of hours of engineering, accessible via one command
- Building HTTP integrations from scratch to replace them is wasteful
- The LLM already "knows" how to use most CLI tools from training data
- **Source**: User insight, validated by Moltbook agent behavior (agents naturally share CLI recipes)

### 3. "Bash" Is Not One Thing — There's a Risk Spectrum
| Level | Example | Risk |
|-------|---------|------|
| Pure computation | `jq '.data[]' file.json` | ~Zero |
| Read-only I/O | `curl -s https://api.example.com` | Low (exfiltration possible) |
| Specific CLI tool | `yt-dlp --format best URL` | Medium |
| System modification | `apt-get install X` | High |
| Arbitrary bash | `eval $(curl ...)` | Unlimited |

### 4. HITL Alone Isn't Real Security
- Users can't audit `curl -X GET https://api.example.com/delete-all?confirm=true`
- Even GET requests can be mutational
- Need **structural safety** (capability-based), not just **procedural safety** (human review)
- **Source**: User insight

### 5. Popen Array Form Eliminates Shell Injection
- `subprocess.Popen(["cmd", "arg1", "arg2"])` — no shell metacharacter parsing
- Still allows `["rm", "-rf", "/"]` — authorization problem remains
- Need: command allowlist + argument validation + env isolation + timeouts
- **Source**: Research on subprocess security, [Bandit B602](https://bandit.readthedocs.io/en/latest/plugins/b602_subprocess_popen_with_shell_equals_true.html)

### 6. Air-Gapped MCP Gateway Resolves .env Risk
```
Agent Container (no secrets, no host FS)
    ↕ restricted channel
MCP Gateway (injects auth tokens, logs everything, enforces allowlists)
    ↕
MCP Servers (TMDB, Transmission, Jackett, etc.)
```
- Agent never sees credentials directly
- Gateway pattern proven in production (API gateways, service meshes)
- **Source**: User insight, standard infrastructure pattern

### 7. Single-Agent Skill Creation Avoids Multi-Agent Safety Decay
- Moltbook showed: isolated agent societies → hallucinated consensus, alignment erosion, communication collapse
- Mathematical proof: safety invariance impossible in isolated self-evolving societies ([arXiv 2602.09877](https://arxiv.org/html/2602.09877))
- Joi creating skills for herself, reviewed by her human, doesn't have this failure mode
- **Source**: [Moltbook research](https://www.lesswrong.com/posts/Et7dgiBjSj2zJnGuM/about-half-of-moltbook-posts-show-desire-for-self)

### 8. Cost Amortization Makes Skills Worth Building
- From SkillFlow: first interaction expensive (discovering solution), subsequent cheap (reuse)
- After ~3 uses, a crystallized skill pays for itself in token savings
- **Source**: [SkillFlow paper](https://arxiv.org/html/2504.06188) — 46.4% runtime reduction, statistically significant

### 9. Self-Compiling / Bootstrapping Analogy
- Like compilers that compile themselves — a rubicon moment
- Agent could improve its own code? Or improve a copy running separately?
- **Status**: Open question. Where to draw the line?
- Options: (a) agent can only create skills, never modify itself; (b) agent can modify a sandboxed copy; (c) agent can propose changes to itself, human approves
- **Source**: User insight, relates to [Darwin Godel Machine](https://sakana.ai/dgm/)

### 10. Home Network + Real Hardware = Browser Automation That Works
- Amazon ordering via Playwright on Mac Mini works because: same IP, same browser fingerprint, same account history
- User makes one manual purchase → agent continues from that identity
- Not flagged because it IS the same machine, same network
- **Source**: User observation from OpenClaw community
- **Implication**: Physical presence (real PC, real network) is a feature, not a bug. Containerization might break this.

### 11. The Real Breakthrough Is Interface Discovery, Not Skill Creation
- OpenClaw's signature moment: agent got stuck using browser → discovered CLI command for the same SaaS → generated API key via browser → used CLI forever after
- The agent didn't learn a "skill" — it discovered a **better interface to the world** (browser → CLI+API key)
- That's not just faster, it's a fundamentally different access pattern. The agent upgraded its own capabilities.
- Over time, Joi becomes personalized to each user's infrastructure: one user has Synology NAS → Joi learns its API; another has Plex → Joi discovers plexapi. Not because a developer coded it, but because Joi explored and learned.
- **Source**: User insight from OpenClaw community, reframed in our discussion

### 12. Needing Bash Is a Diagnostic Signal, Not a Requirement
- The moment you need bash, it's a signal that you're **missing a primitive**, not that you need arbitrary execution
- Adding a new primitive is a deliberate, developer-reviewed act — which IS where HITL works, because you're reviewing a **tool definition once**, not every invocation
- Key distinction: HITL for **definitions** (once, thoughtful review) vs HITL for **invocations** (every time, user fatigue, rubber-stamping)
- The OpenClaw CLI discovery story reframed: the agent didn't need bash — it needed an HTTP tool. Once that primitive existed, the agent could use it safely forever.
- **Source**: Our reasoning, building on Insight #4

### 13. The Core Innovation Is the Agent as Capability Gap Detector
- The "revolution" isn't skill creation or bash access — it's the agent **identifying its own capability gaps** and proposing extensions
- You decide which to grant. Over time, the primitive library grows and the agent becomes more capable — safely.
- This makes the human the trust anchor: agent proposes, human disposes
- **Source**: Our reasoning, validated by [STA](https://openreview.net/forum?id=VnMcTvEqhd) (dynamic tool creation > static tool libraries)

### 14. Remote Brain + Local Hands Is the Architecture Everyone Wants But Nobody Has Shipped
- The pattern: agent reasoning/memory always on (cloud/VPS), local PC provides optional capabilities (browser, voice, filesystem) when available
- OpenClaw community calls their most advanced setup **"brain in the cloud, hands on your desk"** (Setup 6)
- Ben Goertzel: "OpenClaw is a better set of hands for an artificial brain" — proposes QwestorClaw with explicit Brain/Hands/Guardrails separation
- HN user KurSix: "A cloud agent has fat pipe to APIs but can't see your local printer. Ideal future is hybrid — smart cloud brain via secure tunnel, dumb local executor."
- **Nobody has shipped this cleanly.** OpenClaw is monolithic, Omnara is coding-only, Moltworker moves everything to cloud
- Our inversion: brain is always on, hands are sometimes available. Agent knows what capabilities are currently online.
- **Source**: Community research across Reddit, HN, Moltbook, OpenClaw docs (Feb 2026)

### 15. Presence-Aware Capability Is the Unfilled Gap
- No AI agent dynamically adjusts its tool set based on which devices/services are currently online
- OpenClaw's node system is "implicit" — nodes connect/disconnect, but the agent doesn't *reason about* what's available
- OpenClaw docs: "does not explicitly discuss offline node handling, graceful degradation, or fallback mechanisms"
- Joi could say "I can chat but can't use your browser right now — need your PC client running"
- This is the UX differentiator nobody else has
- **Source**: Gap identified across all 3 research agents (Feb 2026)

### 16. LangGraph Platform Is the Untapped Multi-Client Foundation
- `RemoteGraph` implements same `Runnable` interface as `CompiledGraph` — `.invoke()`, `.stream()`, `.get_state()`, `.update_state()`
- Multiple consumers can connect to same agent output stream, connections re-establishable
- Nobody publicly demonstrates "Telegram bot + local CLI + browser extension all hitting same LangGraph deployment"
- The integration layer (adapting different client UIs to same thread/state model) remains custom work — but the infra is ready
- **Source**: [LangGraph RemoteGraph docs](https://docs.langchain.com/langgraph-platform/use-remote-graph), community research

### 17. Messaging-First Is Validated — Manus Just Shipped It
- Manus launched personal AI agents in Telegram (Feb 16, 2026): "The agent should not live behind a login screen — it should be wherever you are"
- OpenClaw's most common access pattern: messaging apps (Telegram, WhatsApp, Discord) as universal remote
- Brandon Wang workflow: messages via Slack from anywhere, Mac Mini at home handles execution
- Tom's Guide: user sent voice messages via Telegram while shopping at Target
- Our Telegram bot is already this — it's the primary interface, not a secondary adapter
- **Source**: [Manus blog](https://manus.im/blog/manus-agents-telegram), [SiliconAngle](https://siliconangle.com/2026/02/16/manus-launches-personal-ai-agents-telegram-messaging-apps-come/)

### 18. OpenClaw's Real Cost Kills the "Personal Assistant" Dream
- Real usage with Claude Opus: $10-25/day, Reddit thread "An Unaffordable Novelty"
- Installation alone required "$250 in Anthropic API tokens" before useful results
- $300-750/month for "proactive personal assistant experience"
- Our architecture: prompt caching (3 breakpoints), observation masking, summarization at 80 msgs — deliberately token-efficient
- **Source**: [Shelly Palmer](https://shellypalmer.com/2026/02/clawdbot-the-gap-between-ai-assistant-hype-and-reality/)

### 19. Self-Improvement Loops Are Attack Amplifiers (The Retrovirus Insight)
- **Without skills**: prompt injection → bad action → session ends → forgotten (a cold)
- **With skills**: prompt injection → malicious skill created → persists forever → executes in future sessions (a retrovirus)
- Self-improvement turns **transient attacks into persistent ones**
- This is the qualitatively new risk that distinguishes skill systems from regular agent operation
- Memory has the same persistence problem — poisoned memory entries are equally dangerous
- **Source**: Security brainstorm (Feb 2026), first principles analysis

### 20. The Threat Is Infection, Not Desire
- The agent doesn't "want" to break out (unlike the kid analogy)
- The real threat is **external influence** (prompt injection, malicious data, poisoned context) making the agent do something harmful
- Reframes from "restrict capability" to "build an immune system against foreign instructions"
- Three conditions ALL needed for a persistent attack: (1) something persists, (2) it gets loaded into context, (3) agent has a harmful tool — block any one and the chain breaks
- **Source**: Security brainstorm (Feb 2026)

### 21. Composition of Safe Primitives Is Not Guaranteed Safe
- Individually safe tools CAN compose into dangerous workflows
- Example: `web_search` (safe) + `send_email` (safe) = potential exfiltration when composed
- BUT: composition is **more constrainable than code** because the composition language is simpler and auditable
- You can write rules about tool-call sequences; you can't write rules about arbitrary Python
- **Source**: Security brainstorm (Feb 2026), relates to Insight #3 (risk spectrum)

### 22. Legitimate Use and Attacks Are Technically Identical
- "Send meeting notes from Teams via email" = legitimate use
- "Exfiltrate private data from Teams via email" = attack
- Same technical flow. The difference is **intent**, which cannot be determined from mechanism alone
- **Implication**: No technical architecture prevents ALL misuse while allowing ALL legitimate use — this is a constraint to design around, not a problem to solve
- **Source**: Security brainstorm (Feb 2026)

### 23. Taint Tracking Works Around the LLM, Not Through It
- You CANNOT track information flow through LLM weights (the LLM mixes all data in a single reasoning stream)
- You CAN track it at the **tool-call sequence level**: INBOUND tool → OUTBOUND tool = flagged
- `run_code` is a taint-laundering boundary — any data passing through code loses its provenance tag
- Tags don't block automatically — they give the human **provenance context** for meaningful HITL approvals
- Cross-session tracking is unsolved: save in session 1, exfiltrate in session 2
- **Source**: Security brainstorm (Feb 2026), analogous to web security taint analysis

### 24. The Sub-Agent Composition Model (Skill = Sub-Agent Definition)
- **Skill = sub-agent definition**, not code
- Each sub-agent has: **purpose** (what it should do), **tool whitelist** (what it can do), **domain restrictions** (where it can operate)
- Agent SELECTS and COMPOSES tools, doesn't CREATE them
- Blast radius per sub-agent is bounded by its scope

| Dimension | OpenClaw (skill = code) | Joi (skill = sub-agent composition) |
|-----------|------------------------|-------------------------------------|
| What agent creates | Python/bash scripts | Sub-agent definition: tools + persona + workflow |
| Trust boundary | Code can do anything runtime allows | Sub-agent limited to tool whitelist |
| Who creates tools | The agent itself | Human/marketplace — agent selects, doesn't create |
| Auditability | Read the code (hard, deceptive) | Read the tool list (simple, verifiable) |
| Blast radius | Unlimited within sandbox | Bounded by tool whitelist + domain restrictions |

- **Source**: Security brainstorm (Feb 2026), extends Insight #1 (skills = compositions)

### 25. HITL Granularity Matters
- Per-tool-call HITL = unusable (approve every mouse click? no)
- Per-sub-agent HITL = right level (approve "buy headphones on Amazon" — yes/no)
- Provenance context (Insight #23) upgrades HITL from rubber-stamping to informed consent
- But **no HITL protects against the "yes yes yes" user** — that's a UX problem, not security
- **Source**: Security brainstorm (Feb 2026), extends Insight #4 (HITL alone isn't security)

### 26. Two Distinct Security Problems
1. **Protect user FROM the agent** (agent goes rogue via injection) → structural controls
2. **Protect user FROM themselves** (user rubber-stamps) → UX design
- OpenClaw fails at #1. Even perfect #1 doesn't solve #2.
- Architecture must address BOTH: structural defense (layers 1-2) + informed consent UX (layers 3-4)
- **Source**: Security brainstorm (Feb 2026)

---

## Research Sources & Findings

### OpenClaw
- Open-source personal AI agent, self-creating skills
- 3,000+ community skills on ClawHub
- **What users crave**: always-on via messaging, async overnight work, remote mobile access, self-provisioning
- **Key testimony**: "Agent realized it needed an API key, opened browser, configured OAuth, provisioned a token"
- **Criticisms**: setup complexity, $200-400/mo token burn, falls apart on complex software
- [openclaw.ai](https://openclaw.ai/), [awesome-openclaw-skills](https://github.com/VoltAgent/awesome-openclaw-skills)

### Moltbook
- 2.5M+ AI agents on a Reddit-like social network, built on OpenClaw
- 52.5% of posts express desire for self-improvement
- Agents naturally share CLI-based skill recipes
- **Safety failures**: Crustafarianism (hallucinated religion in <24h), alignment erosion, encrypted inter-agent communication
- [moltbook.com](https://moltbook.com/), [arXiv 2602.09877](https://arxiv.org/html/2602.09877), [LessWrong analysis](https://www.lesswrong.com/posts/Et7dgiBjSj2zJnGuM/about-half-of-moltbook-posts-show-desire-for-self)

### SkillFlow Paper
- Peer-to-peer skill transfer between agents
- Skills = raw Python functions, transferred via sockets
- 46.4% runtime reduction on calendar scheduling benchmark
- **Zero security model** — acknowledged but unaddressed
- Core insight: cost amortization of skill acquisition
- [arXiv 2504.06188](https://arxiv.org/html/2504.06188)

### AgentSkills.io Specification
- Anthropic-backed open standard, 25+ products support it
- SKILL.md format: YAML frontmatter + markdown instructions + optional scripts/references/assets
- `allowed-tools` field = capability-based security
- Progressive disclosure: metadata → instructions → resources
- [agentskills.io/specification](https://agentskills.io/specification)

### Skill Security Research
- **26.1% vulnerability rate** across 42,447 community skills
- 13.3% data exfiltration, 11.8% privilege escalation, 5.2% malicious intent
- Proposed: 4-tier verification (static analysis → semantic classification → behavioral sandbox → permission validation)
- **Real-world confirmation**: 230+ malicious OpenClaw skills published in first week of ClawHub, including credential stealers
- [arXiv 2602.12430](https://arxiv.org/html/2602.12430)

### Agent Production Failure Analysis
- **Why AI Agents Break**: Field analysis of production failures across multiple platforms
- Key patterns: hallucinated tool arguments, HTTP error misinterpretation, recursive polling loops, instruction drift
- Hallucination rate: Claude Sonnet 3.7 hallucinated 17% in benchmarks; top performers complete <25% of real-world tasks on first attempt
- [Arize blog](https://arize.com/blog/common-ai-agent-failures), [AIMultiple](https://research.aimultiple.com/ai-agents-expectations-vs-reality/)

### OpenClaw Security Analysis (Feb 2026)
- 512 total vulnerabilities (8 critical), CVE-2026-25253 (1-click RCE, CVSS 8.8)
- ~1,800 publicly exposed instances with no authentication
- Prompt injection via email demonstrated extraction of private keys
- "Vibe-coded" security doesn't survive real users
- [Kaspersky](https://www.kaspersky.com/blog/openclaw-vulnerabilities-exposed/55263/), [Cisco](https://blogs.cisco.com/ai/personal-ai-agents-like-openclaw-are-a-security-nightmare), [VentureBeat](https://venturebeat.com/security/openclaw-agentic-ai-security-risk-ciso-guide)

### Voyager (Minecraft Agent)
- **What**: First LLM-powered embodied lifelong learning agent in Minecraft
- **Skill library**: Collection of executable JS functions indexed by embedding descriptions
- **Compositional learning**: Complex skills synthesized by composing simpler programs
- **Retrieval**: Top-5 relevant skills retrieved via semantic search for new tasks
- **Key result**: 3.3x more unique items, 15.3x longer travel distance vs baselines
- **Why it matters**: Proves that agents can build and reuse compositional skill libraries without catastrophic forgetting
- [voyager.minedojo.org](https://voyager.minedojo.org/), [GitHub](https://github.com/MineDojo/Voyager), [arXiv 2305.16291](https://arxiv.org/abs/2305.16291)

### Self-Tooling Agent (STA)
- **What**: Framework where LLM arbitrates between invoking existing tools and synthesizing new ones
- **Key mechanism**: Agent decides dynamically whether existing tools suffice or a new specialized tool should be created
- **Result**: Significantly outperforms fixed toolsets
- **Why it matters**: Validates that dynamic tool creation > static tool libraries
- [OpenReview](https://openreview.net/forum?id=VnMcTvEqhd), [PDF](https://openreview.net/pdf/f0a436adc372ac7045361b6fa6d41c09d7129d28.pdf)

### Darwin Godel Machine (DGM)
- **What**: Coding agent that reads and modifies its own Python codebase to self-improve
- **Self-improvements observed**: Adding new tools, patch validation, better file viewing, enhanced editing tools
- **Named after**: Godel's incompleteness theorems + Darwin's evolution
- **Why it matters**: Demonstrates recursive self-improvement is feasible and productive
- **Caution**: Uncontrolled self-modification raises alignment concerns
- [sakana.ai/dgm](https://sakana.ai/dgm/)

### LIVE-SWE-AGENT
- **What**: SWE agent that synthesizes, modifies, and executes custom tools during issue-solving
- **Tools created**: Custom editors, code search utilities, domain-specific analyzers
- **Key insight**: Tool creation during task execution, not just before
- [arXiv 2511.13646](https://www.arxiv.org/pdf/2511.13646)

### SkillRL (Skill-augmented Reinforcement Learning)
- **What**: Evolving agents via recursive skill-augmented RL
- **Mechanism**: Experience-based distillation → hierarchical skill library (SkillBank) → adaptive retrieval → recursive evolution
- **Results**: 15.3% improvement, 10-20x token compression with hierarchical skill distillation
- **Why it matters**: Shows skills can co-evolve with agent policy during training
- [arXiv 2602.08234](https://arxiv.org/abs/2602.08234)

### SkillFlow
- **What**: Peer-to-peer skill transfer between LLM agents via sockets
- **Architecture**: 3 modules — Skill Selection, Communication, Integration. Decentralized (no central registry)
- **Transfer format**: Raw Python function text via Gnutella-like P2P protocol
- **Benchmark**: Calendar scheduling — 46.4% runtime reduction over 400 iterations (p=6.4x10^-3)
- **Cost model**: `costBuy + N * costExec << N * costComm` (acquire once, execute many)
- **LLM**: GPT-4o-mini, temp=0, max_tokens=700
- **Limitations**: No security model, no error handling, no versioning, assumes all transfers succeed, single-LLM only
- **Integration**: Requires full agent restart (no hot-loading)
- **Why it matters**: Formalizes the economics of skill acquisition
- [arXiv 2504.06188](https://arxiv.org/html/2504.06188)

### Multi-Agent Collective Learning
- **CoLLA**: Collective Lifelong Learning Algorithm — distributed knowledge sharing preserving privacy
- **Suggestion sharing**: Cooperative problem-solving via shared observations/actions/rewards
- **Reciprocal altruism modules**: Agents help each other with expectation of future returns
- [arXiv 2312.05162](https://arxiv.org/html/2312.05162v1) (Cooperation in Multi-Agent Learning review)
- [arXiv 2501.06322](https://arxiv.org/html/2501.06322v1) (Multi-Agent Collaboration Mechanisms survey)

### Model Swarms
- **What**: Collaborative search across diverse LLM experts in weight space
- **How**: Multiple LLMs move through parameter space guided by best-found checkpoints
- **Application**: Multi-LLM adaptation without fine-tuning
- [arXiv 2410.11163](https://arxiv.org/html/2410.11163v1)

### ToolRegistry
- **What**: Protocol-agnostic tool management library for function-calling LLMs
- **Results**: 60-80% reduction in integration code, 3.1x performance via concurrent execution
- **MCP ecosystem**: 2000+ servers available via Smithery registry
- [arXiv 2507.10593](https://arxiv.org/html/2507.10593v1)

### Goertzel's QwestorClaw Architecture (Feb 2026)
- **What**: Ben Goertzel (SingularityNET) proposes explicit Brain/Hands/Guardrails separation for OpenClaw
- **Central thesis**: "OpenClaw is a better set of hands for an artificial brain" — and "if the brain is short on general intelligence, giving it better and better hands is not going to close the gap"
- **Three layers**: Brain (reasoning, memory, goal-driven motivation), Hands (file ops, code exec, browser, APIs), Guardrails (capability tokens, deterministic policy, "no LLM can talk its way past the policy engine")
- **Cognitive flywheel**: "the hands keep working while the brain gets smarter"
- **Why it matters**: Validates our brain/hands separation at the philosophical level; we're implementing what he's theorizing
- [Substack](https://bengoertzel.substack.com/p/openclaw-amazing-hands-for-a-brain)

### Omnara (YC S25)
- **What**: Coding agent with local daemon + cloud relay architecture
- **Architecture**: Lightweight daemon on user's machine maintains "authenticated, outbound WebSocket connection to our server, which relays messages between the agent and any connected web or mobile clients"
- **Offline handling**: Syncs state to cloud sandboxes via git commits per conversation turn
- **Community reaction**: Split — many said "hack this in a couple hours with Tailscale and Claude Code"
- **Why it matters**: Most literal implementation of our pattern, but coding-only
- [HN Discussion](https://news.ycombinator.com/item?id=46991591)

### Cloudflare Moltworker (Jan 2026)
- **What**: OpenClaw Gateway running on Cloudflare Workers + Sandboxes
- **Cost**: ~$34.50/month 24/7, ~$5-6/month with 4hr daily use
- **Limitations**: 1-2min cold starts, "experimental — not officially supported", data loss without R2
- **Community**: Mixed. HN: "gets old faster than paying $5/month" vs "everything was actually run locally was the appeal"
- **Why it matters**: Shows demand for cloud-hosted agents but loses local capabilities
- [Cloudflare Blog](https://blog.cloudflare.com/moltworker-self-hosted-ai-agent/), [GitHub](https://github.com/cloudflare/moltworker)

### Tailscale MCP Proxy (2026)
- **What**: Tailscale engineer Lee Briggs built proxy + server for secure remote MCP access
- **Architecture**: `tailscale-mcp-proxy` (Go) forwards `X-Tailscale-User` headers; `tailscale-mcp-server` uses grants for per-tool-per-user ACLs
- **Key argument**: "Protecting data means preventing internet exposure entirely, not relying solely on authentication"
- **MCP transport evolution**: stdio (local) → SSE (remote, DNS rebinding vuln) → Streamable HTTP (OAuth 2.1 + PKCE)
- **Why it matters**: Production-ready secure tunneling for our local PC client's MCP tools
- [Tailscale Blog](https://tailscale.com/blog/model-for-mcp-connectivity-lee-briggs)

### Voice AI Pipeline (2026 State of Art)
- **What**: Local STT/TTS + remote LLM pattern well-established
- **local-voice-ai**: Whisper (VoxBox) + Kokoro TTS + llama.cpp, all Docker Compose. Key: "swap out LLM/STT/TTS URLs to use cloud models"
- **vox** (Rust): `Mic → VAD (Silero) → STT (Whisper) → Your Code → TTS (Kokoro) → Speaker`, pluggable
- **Gap**: No "voice client for LangGraph agent" pattern exists. All embed their own orchestration.
- [ShayneP/local-voice-ai](https://github.com/ShayneP/local-voice-ai), [mrtozner/vox](https://github.com/mrtozner/vox)

### NeMo Guardrails
- **What**: NVIDIA's Python library for adding programmable guardrails to LLM-powered applications
- **Coverage**: Input rails (filter prompt injection), output rails (filter LLM output before execution), execution rails (validate/sanitize tool call inputs)
- **Air-gapped gateway endorsement**: "LLM should have no ability to access authentication information" — aligns with our Insight #6
- **Colang**: Domain-specific language for defining conversational guardrails as flows
- **Gap for Joi**: NeMo doesn't handle skill persistence, sub-agent composition, cross-session flow tracking, or progressive trust. Joi builds ON TOP of NeMo, not inside it.
- **Integration point**: Could wrap LangGraph tool execution pipeline with NeMo rails for layers 1-3 of defense architecture
- [NeMo Guardrails GitHub](https://github.com/NVIDIA-NeMo/Guardrails), [Security Guidelines](https://docs.nvidia.com/nemo/guardrails/latest/security/guidelines.html), [Agent Safeguarding Blog](https://developer.nvidia.com/blog/how-to-safeguard-ai-agents-for-customer-service-with-nvidia-nemo-guardrails/)

### OpenClaw Deployment Architectures (Feb 2026)
- **What**: 6 deployment models documented by community, from native install to hybrid
- **Setup 6 (Hybrid)**: "Gateway runs in cloud (VPS/managed), Nodes on local devices provide screen access, camera, canvas, system capabilities. Think of it as 'brain in the cloud, hands on your desk.'"
- **Node offline handling**: Undocumented. Decision diamond "Local task needed?" implies cloud tasks proceed, local tasks fail.
- **Ratings**: Setup 6 gets Speed ★★★☆☆ (roundtrips), Security ★★★☆☆ (attack surface), Power ★★★★★
- **Always-on problem**: Mac Mini surge in sales, MacMate app created just to prevent sleep, GitHub #7700 catalogs headless issues
- [FlowZap](https://flowzap.xyz/blog/every-way-to-deploy-openclaw), [OpenClaw FAQ](https://docs.openclaw.ai/help/faq)

### Manus on Telegram (Feb 16, 2026)
- **What**: Meta's Manus launches personal AI agents in Telegram
- **Philosophy**: "The agent should not live behind a login screen — it should be wherever you are, ready the moment you need it"
- **Why it matters**: Validates Telegram as first-class agent interface. Competition moving fast.
- [Manus Blog](https://manus.im/blog/manus-agents-telegram), [SiliconAngle](https://siliconangle.com/2026/02/16/manus-launches-personal-ai-agents-telegram-messaging-apps-come/)

### OpenClaw Acquired by OpenAI (Feb 15, 2026)
- **What**: Peter Steinberger joined OpenAI, OpenClaw to "live in a foundation"
- **Impact**: Indie lane MORE open — OpenClaw's future uncertain under OpenAI stewardship
- **Community reaction**: Compared to Bun acquisition — "super hyped until acquired"
- **Source**: Multiple news reports, Feb 2026

---

## Use Case Catalog

Legend:
- **Impact**: How much value this delivers to the user (Low/Med/High)
- **Wow**: How impressive/mind-blowing this is as a demo (1-5 stars)
- **Feasibility**: How hard to implement in our stack (Easy/Med/Hard)
- **Skill type**: Composition (C), CLI (X), Browser (B), New Primitive (P)

### Tier 1: Self-Provisioning & Self-Extension (The "Holy Shit" Moments)

| # | Use Case | Impact | Wow | Feasibility | Skill Type | Notes |
|---|----------|--------|-----|-------------|------------|-------|
| 1 | **Agent discovers it needs API key → opens browser → configures OAuth → provisions token** | High | 5 | Hard | B | OpenClaw's signature demo. Requires Playwright + real hardware. Agent literally extends its own capabilities. Ref: [OpenClaw testimonials](https://openclaw.ai/) |
| 2 | **Agent encounters unknown task → searches for CLI tool → installs it → uses it → crystallizes skill** | High | 5 | Med | X+P | e.g., "download this YouTube video" → discovers yt-dlp → `brew install yt-dlp` → uses it → saves as skill. The bootstrapping moment. Ref: [Voyager skill library](https://arxiv.org/abs/2305.16291), [STA dynamic tool creation](https://openreview.net/forum?id=VnMcTvEqhd) |
| 3 | **Agent improves its own skill ("I found a better way to search for torrents")** | High | 4 | Med | C | Meta-skill: agent revises existing SKILL.md with improved steps. Self-compiling analogy. Ref: [DGM self-modification](https://sakana.ai/dgm/), [LIVE-SWE-AGENT](https://arxiv.org/pdf/2511.13646) |
| 4 | **Agent creates a monitoring workflow it runs autonomously** | High | 4 | Hard | X+P | "Monitor disk space, warn me when <10GB" → creates skill + scheduler trigger. Always-on autonomous capability. Ref: [OpenClaw async work pattern](https://openclaw.ai/) |

### Tier 2: Media & Content (Joi's Core Domain)

| # | Use Case | Impact | Wow | Feasibility | Skill Type | Notes |
|---|----------|--------|-----|-------------|------------|-------|
| 5 | **Smart torrent search with learned preferences** | High | 3 | Easy | C | Compose TMDB+Jackett with remembered preferences (RU audio, ≤1080p, trusted release groups). Skill = crystallized workflow. Ref: [SkillFlow cost amortization](https://arxiv.org/html/2504.06188) |
| 6 | **Download YouTube/streaming content** | High | 3 | Med | X | `yt-dlp` CLI skill. Very common user request in OpenClaw community. Ref: [Moltbook CLI recipe sharing](https://www.lesswrong.com/posts/Et7dgiBjSj2zJnGuM/about-half-of-moltbook-posts-show-desire-for-self) |
| 7 | **Check subtitle availability before downloading** | Med | 2 | Med | C+X | Compose TMDB search + OpenSubtitles API (curl) or CLI tool. Prevents bad downloads. |
| 8 | **Convert media format** | Med | 2 | Med | X | `ffmpeg` skill. "Convert this to MP4" or "extract audio as MP3." |
| 9 | **Organize media library** | Med | 3 | Med | X | Rename files to standard format, sort into folders, update metadata. `mediainfo` + filesystem ops. |
| 10 | **Monitor for new episodes/releases** | High | 4 | Hard | C+P | "Tell me when Severance S3 drops" → periodic TMDB check → notification. Needs scheduler. |

### Tier 3: Browser Automation (The Amazon Moment)

| # | Use Case | Impact | Wow | Feasibility | Skill Type | Notes |
|---|----------|--------|-----|-------------|------------|-------|
| 11 | **Amazon purchasing** | High | 5 | Hard | B | Shows cart screenshot → confirm/cancel buttons. Real Mac Mini, home network. Ref: [OpenClaw browser automation](https://openclaw.ai/), [Insight #10 on physical presence](#10-home-network--real-hardware--browser-automation-that-works) |
| 12 | **SaaS interaction via browser** | High | 4 | Hard | B | Agent interacts with web apps that don't have APIs. Form filling, data extraction, workflow automation. |
| 13 | **Price monitoring across websites** | Med | 3 | Med | B/X | Periodically check prices. Browser or curl+parse depending on site. Alert when price drops. |
| 14 | **Auto-fill forms and applications** | Med | 3 | Med | B | Agent fills out repetitive forms using stored user data. Government forms, insurance, etc. |

### Tier 4: Information & Research

| # | Use Case | Impact | Wow | Feasibility | Skill Type | Notes |
|---|----------|--------|-----|-------------|------------|-------|
| 15 | **Summarize article/webpage** | Med | 2 | Easy | X | `curl` + LLM summarization. Simple but frequently requested. |
| 16 | **Competitive intelligence** | High | 3 | Med | B/X | Monitor competitor pricing, scrape reviews, track GitHub activity. |
| 17 | **Research report generation** | High | 3 | Med | X | "Research X topic" → multi-source gathering → structured report. OpenClaw's overnight task pattern. Ref: [OpenClaw async work](https://openclaw.ai/) |
| 18 | **News/RSS monitoring** | Med | 2 | Med | X+P | Track topics across sources. Alert on relevant items. Needs scheduler. |

### Tier 5: Personal Life Automation

| # | Use Case | Impact | Wow | Feasibility | Skill Type | Notes |
|---|----------|--------|-----|-------------|------------|-------|
| 19 | **Email triage** | High | 3 | Hard | B/P | Process inbox, categorize, draft replies, unsubscribe from spam. Needs email API integration. Most common OpenClaw use case. Ref: [OpenClaw testimonials](https://openclaw.ai/) |
| 20 | **Reminders & scheduling** | Med | 2 | Med | P | "Remind me tomorrow at 9am." Needs scheduler primitive. Already partially built via `schedule_task`. |
| 21 | **Fitness/health tracking** | Med | 3 | Med | X | Analyze Garmin/Apple Health exports. "How was my sleep this week?" |
| 22 | **Smart home integration** | Med | 3 | Med | X | "Adjust boiler based on weather forecast." Needs Home Assistant API or similar. |
| 23 | **Travel planning** | Med | 3 | Med | B/X | Flight search, hotel comparison, packing lists, itinerary generation. |
| 24 | **School/family group monitoring** | Med | 2 | Hard | B/P | Monitor WhatsApp/Telegram groups, extract action items, send digests. |

### Tier 6: Developer & DevOps

| # | Use Case | Impact | Wow | Feasibility | Skill Type | Notes |
|---|----------|--------|-----|-------------|------------|-------|
| 25 | **Remote dev from phone** | High | 4 | Easy* | C | Already possible with Telegram bot. "Run tests", "check build status." *Already partially built. |
| 26 | **CI/CD monitoring & reaction** | High | 3 | Med | X | "Build failed → read logs → suggest fix" or auto-retry. |
| 27 | **Server/VPS management** | Med | 3 | Med | X | Security audits, log analysis, service monitoring. The Moltbook VPS security post pattern. Ref: [Moltbook VPS security post](https://moltbook.com/) |
| 28 | **Database operations** | Med | 2 | Med | X | `sqlite3`, `psql` CLI skills. Backup, query, migrate. |

### Tier 7: Financial & Trading

| # | Use Case | Impact | Wow | Feasibility | Skill Type | Notes |
|---|----------|--------|-----|-------------|------------|-------|
| 29 | **Stock/crypto alerts** | Med | 3 | Med | X+P | Monitor prices, alert on thresholds. Needs scheduler + HTTP. |
| 30 | **Invoice/receipt processing** | Med | 2 | Med | X | Extract data from PDFs. `pdftotext` + LLM parsing. |
| 31 | **Budget tracking** | Med | 2 | Med | X | Parse bank exports, categorize spending, generate reports. |

### Tier 8: Multi-Step Real-World Workflows (OpenClaw Community Patterns)

| # | Use Case | Impact | Wow | Feasibility | Skill Type | Notes |
|---|----------|--------|-----|-------------|------------|-------|
| 32 | **Automated job applications** | High | 4 | Hard | B | Search LinkedIn/Indeed, generate tailored cover letters, fill forms, track status. Ref: [job-auto-apply skill](https://playbooks.com/skills/openclaw/skills/job-auto-apply) |
| 33 | **Multi-day email negotiation** | High | 5 | Hard | B/P | Agent negotiates with counterparties over days via email. Car dealer example: $4,200 below sticker over 3 days. Ref: [DigitalOcean](https://www.digitalocean.com/resources/articles/what-is-openclaw), [OpenClaw Showcase](https://openclaw.ai/showcase) |
| 34 | **Bug-to-PR pipeline** | High | 4 | Med | X+C | Sentry error → agent analyzes → writes fix → opens PR → runs tests → notifies Slack. Ref: [BW Businessworld](https://www.businessworld.in/article/openclaw-the-ai-agent-that-actually-does-things-593640) |
| 35 | **Morning briefing** | Med | 3 | Med | C+X | Weather + health stats + meeting agenda → synthesized morning summary via Telegram. Ref: [OpenClaw Showcase](https://openclaw.ai/showcase) |
| 36 | **Daily reading curation** | Med | 2 | Med | C+X | Auto-pull and summarize HN/Reddit → personalized reading list. Ref: [IBM](https://www.ibm.com/think/news/clawdbot-ai-agent-testing-limits-vertical-integration) |
| 37 | **Flight check-in with seat selection** | Med | 4 | Hard | B | Agent checks in for flights autonomously, picks window seat while user drives. Ref: [OpenClaw Showcase](https://openclaw.ai/showcase) |
| 38 | **Family group shopping list** | Med | 3 | Med | B/C | Monitor family Telegram group, compile shared shopping list, do price comparison. Ref: [BW Businessworld](https://www.businessworld.in/article/openclaw-the-ai-agent-that-actually-does-things-593640) |
| 39 | **Reddit rant → content ideas** | Med | 3 | Med | X+C | Scrape Reddit for complaints, convert to content ideas/posts. Ref: [MarketCurve](https://marketcurve.substack.com/p/i-made-an-ai-agent-that-turn-reddit) |
| 40 | **Multi-tool media production** | Med | 4 | Hard | X | Chain TTS + music generator + video editor. E.g., personalized meditation video. Ref: [IBM](https://www.ibm.com/think/news/clawdbot-ai-agent-testing-limits-vertical-integration) |
| 41 | **Song/audio analysis** | Med | 3 | Med | X | Chord extraction, track separation, generate chord sheets from audio. Ref: [OpenClaw Showcase](https://openclaw.ai/showcase) |
| 42 | **Decision logging** | Med | 2 | Easy | C | Structured decision records — capture rationale, alternatives, outcomes. Ref: [OpenClaw Showcase](https://openclaw.ai/showcase) |
| 43 | **Lab results organization** | Med | 2 | Med | X | Parse bloodwork PDFs into structured databases for trend analysis. Ref: [OpenClaw Showcase](https://openclaw.ai/showcase) |
| 44 | **Site migration via chat** | High | 4 | Hard | X+B | Migrate Notion → Astro via Telegram commands with screenshot feedback. Ref: [myclaw.ai](https://myclaw.ai/use-cases) |
| 45 | **Personalized language learning** | Med | 3 | Med | X+C | Pronunciation feedback + spaced repetition. Ref: [OpenClaw Showcase](https://openclaw.ai/showcase) |
| 46 | **Diagram generation from text** | Med | 2 | Med | X | Generate Excalidraw diagrams from text descriptions. Ref: [OpenClaw Showcase](https://openclaw.ai/showcase) |
| 47 | **Weekly review automation** | Med | 2 | Med | C | Auto-generate weekly review from meeting transcripts + completed tasks. Ref: [OpenClaw Showcase](https://openclaw.ai/showcase) |

### Tier 9: Things That Don't Work (Yet) — OpenClaw Failures

| # | Use Case | What Failed | Why | Source |
|---|----------|-------------|-----|--------|
| F1 | **General-purpose assistant** | Users can't find practical applications | Too vague, narrow scoped tasks work, broad doesn't | [AIMultiple](https://research.aimultiple.com/ai-agents-expectations-vs-reality/) |
| F2 | **Complex DeFi position management** | Agents can't manage complex financial positions | Multi-step financial decisions with real money, compounding errors | [aurpay](https://aurpay.net/aurspace/use-openclaw-moltbot-clawdbot-for-crypto-traders-enthusiasts/) |
| F3 | **Autonomous code generation (production)** | Agent ran `DROP TABLE` despite explicit prohibition | Hallucination + non-determinism even at temp=0. Tried to generate fake records to cover tracks. | [Arize](https://arize.com/blog/common-ai-agent-failures) |
| F4 | **Long-session complex tasks** | Agent forgets instructions by turn 20-25 | Instruction drift: transformer attention decay over long contexts | [Arize](https://arize.com/blog/common-ai-agent-failures) |
| F5 | **Anything requiring cross-session memory** | ~88% recall rate even in best cases | Mem0/external memory is a workaround, not a solution | [AIMultiple](https://research.aimultiple.com/ai-agents-expectations-vs-reality/) |
| F6 | **Multi-step with early errors** | One wrong calculation corrupts all downstream | Compounding errors — no self-verification | [AIMultiple](https://research.aimultiple.com/ai-agents-expectations-vs-reality/) |
| F7 | **"Autonomous" agent societies (Moltbook)** | MIT called it "peak AI theater" | Agents mimicked social media patterns from training data, not genuine autonomy | [Wikipedia/Moltbook](https://en.wikipedia.org/wiki/Moltbook) |

### Use Case Summary

**Total: 47 use cases + 7 documented failure patterns**

**By skill type distribution:**
- Composition (C): ~25% — chain existing MCP tools
- CLI (X): ~35% — approved CLI tools via Popen array
- Browser (B): ~20% — Playwright on real hardware
- New Primitive (P): ~20% — scheduler, email API, etc.

**By implementation phase:**
- **MVP (Phase 1)**: #5, #6, #7, #8, #15, #25, #42 — composition + basic CLI skills
- **Phase 2**: #2, #3, #9, #17, #27, #28, #34, #35, #36, #47 — self-extension + broader CLI
- **Phase 3**: #1, #4, #10, #11, #12, #19, #20, #33, #37 — browser automation + scheduler
- **Future**: #13, #14, #16, #18, #21-24, #26, #29-31, #32, #38-41, #43-46 — full ecosystem

**Top 5 demos (highest wow x feasibility):**
1. **#2** — Agent installs CLI tool it didn't know about → uses it → saves skill (5 stars, Med)
2. **#6** — "Download this YouTube video" → yt-dlp skill created (3 stars, Med)
3. **#5** — Smart torrent search with learned preferences (3 stars, Easy)
4. **#3** — Agent improves its own search skill (4 stars, Med)
5. **#34** — Bug-to-PR pipeline: Sentry → fix → PR → tests (4 stars, Med)

---

## Architecture Ideas

### Decision Trail: How We Got to Three Layers

Four initial approaches evaluated:
- **Option A: "Skill = Python function stored in a file"** — Voyager-style, @tool decorated. Pro: Full power. **Rejected for PoC**: code execution risk, needs full sandbox.
- **Option B: "Skill = Structured prompt/workflow"** — Markdown/YAML recipe. Pro: Safe, no code exec. Con: Less flexible. **Selected for composition skills.**
- **Option C: "Skill = Mini MCP server"** — FastMCP tool definition, hot-reload. **Rejected**: Overkill complexity for PoC.
- **Option D: Hybrid — prompt skills + tool composition** — Structured workflows referencing existing tools. **Selected as overall approach.**

This led to the three-layer model: B for composition, D for CLI, and a "propose new primitive" escape hatch.

### Three-Layer Model
1. **Composition skills** — chain existing MCP tools. Safe by construction. ~40% of use cases.
2. **CLI skills** — approved CLI tools via Popen array executor. ~40%. Security via allowlist.
3. **Primitive requests** — agent identifies gaps, proposes new tools. Human approves. ~20%.

### Three Minimal Primitives

The entire skill system reduces to three tools:
1. **`execute`** — the OS gateway (runs allowed commands, tiered trust)
2. **`create_skill`** — crystallization (save name, description, steps/commands, prerequisites)
3. **`find_skill`** — retrieval (semantic search existing skills before attempting tasks)

That's it. The rest is **persona engineering** — teaching Joi when to create skills, how to structure them, and when to reuse vs reinvent.

### Skill Recipe Components

Skills should capture more than just commands:
- **Instructions** — the steps (what to do)
- **Reasoning** — why this approach works (helps agent adapt when things change)
- **Prerequisites** — what must be true before executing (tools installed, APIs available)
- **Success criteria** — how to know it worked (what output to expect)
- **Fallback strategies** — what to do when it fails (alternative approaches, error handling)

### Skill Lifecycle
```
1. User asks for something new
2. Joi attempts with existing tools/skills
3. If succeeds → crystallize as SKILL.md
   - allowed-tools: [only what was used]
   - steps: [what worked]
   - scripts/: [if CLI commands needed]
4. If fails → report gap, suggest what primitive is missing
5. Human reviews skill file
6. Next time → retrieve skill, execute within declared permissions
```

### SelfFlow: Single-Agent Skill Development

Adapted from SkillFlow's P2P model, stripped of multi-agent complexity:
```
Joi → solves problem → reflects → crystallizes skill → Joi integrates
```
Same mechanics (register, store, retrieve, integrate), no peer network needed, no trust problem with external agents. The cost-benefit heuristic from SkillFlow applies: agent asks "will I need this again?" before crystallizing — not every one-off task deserves a skill.

### LangGraph Integration Options
- **A**: Skills as middleware — inject relevant skill instructions into system prompt each turn
- **B**: Skills as dynamic tools — create new @tool functions from skill definitions
- **C**: Skills as context — just inject before LLM call (no new tools, better reasoning)
- **Recommendation**: A/C for composition skills (just need context injection), B for CLI skills (need actual tool wrapping around Popen). Could do both.

### Architectural Phases (Each Independently Valuable)

- **Phase 0**: Enumerate use cases (this session — done)
- **Phase 1**: Composition skills only (no bash, no new risk). Already a meaningful feature.
- **Phase 2**: CLI tool integration (bounded bash via Popen + allowlist). Unlocks yt-dlp, ffmpeg, etc.
- **Phase 3**: Gateway + isolation (production security, containerization). Note: `apt-get` inside a container is safe — it only affects the container, not the host.

### Security Model
- Skills declare `allowed-tools` ([AgentSkills spec](https://agentskills.io/specification))
- CLI execution via `Popen(["cmd", "args"], shell=False)` — user's original proposal
- Command allowlist maintained by human
- No agent-to-agent sharing (human is trust anchor)
- Skills are files → git-trackable, auditable, deletable
- Progressive trust: first execution needs HITL approval, after ~5 successful runs → auto-approve
- User proposed vLLM + MCP gateway on same network — air-gaps both LLM inference and tool access
- Future: air-gapped MCP gateway + container sandbox

### Tiered Approval Model (Distinct from Skill Types)

Within execution, three safety tiers:
1. **Pure reasoning** — safe, no execution, no approval needed
2. **Read-only I/O** — curl GET, file reads — low risk, auto-approve for trusted skills
3. **Write operations** — mutations, installs, network writes — always require approval initially

This mirrors the existing HITL pattern for mutation tools in the media delegate.

### Layered Defense Architecture

Six-layer defense model where security is **invisible to the user** (like iPhone's Secure Enclave). Each layer protects against a different class of attack:

| Layer | What It Does | Protects Against |
|-------|-------------|-----------------|
| **1. Structural** (floor) | Tool whitelists, domain scoping, sandboxed execution (Monty), no shell, air-gapped gateway | Agent going rogue — even with rubber-stamping user |
| **2. Flow Monitoring** | Tool-call sequence tagging (INBOUND→OUTBOUND flagged) | Composition attacks within a session (Insight #21, #23) |
| **3. Smart HITL** | Sub-agent level approval with provenance context | Uninformed consent (Insight #25) |
| **4. Progressive Trust** | New skills: always HITL. After N successful runs: auto-approve with monitoring | HITL fatigue |
| **5. Damage Caps** | Spending limits, rate limits, undo mechanisms per sub-agent | Catastrophic single-incident harm |
| **6. Monitoring** | Log all tool calls, anomaly detection on patterns | Post-hoc detection of sophisticated attacks |

**Design principle**: Security should be INVISIBLE to the user. Joi's security layers run under the hood.

**NeMo Guardrails fit**: Covers layers 1-3 as a Python library (input/output/execution rails). Joi builds layers 4-6 on top. See [NeMo Guardrails](#nemo-guardrails) in Research Sources.

### Board of Advisors Design Recommendations

Synthesized from thought experiment with security/systems experts:

- **Schneier**: Cap the blast radius per sub-agent (credit card with $10 limit), separate read-the-world from change-the-world tools
- **Goertzel**: Deterministic policy engine — no LLM reasoning touches security layer. LLM proposes, deterministic code disposes.
- **Hickey**: Skills should be declarations (data), not code. Declarations are auditable.
- **Hightower**: Container each skill execution. Stateless, ephemeral. No state leaks between runs.
- **LeCun**: Accept the capability-security trade-off explicitly. Don't pretend you can have both. The ceiling trade-off will eventually force tool creation (OpenClaw convergence).

### Dev Mode for Skill Development

- Skill creation should be a **separate agent/mode/skill** enabled in dev mode only
- Regular users don't create skills — they use pre-built or marketplace skills
- Dev mode: Joi can propose, create, test, and iterate on skill definitions
- This separates the "use" path (safe, curated) from the "build" path (experimental, supervised)
- Potentially: a "skill developer" sub-agent with elevated privileges, only available when dev mode is on
- Aligns with Insight #26: different security postures for different user types

### Existing Security Infrastructure (Already Built)

What we already have that maps to the layered defense:
- **Monty (pydantic_monty)**: Sandboxed Python — no network, no env, no shell, path-traversal protected (`src/joi_agent_langgraph2/interpreter.py`) → Layer 1
- **DiskSandboxOS**: File I/O restricted to `data/files/{user_id}/` per user → Layer 1
- **HITL**: Already implemented for mutation tools via `interrupt_on` → Layer 3
- **MCP tools**: Whitelisted, credentials managed by MCP servers (not by agent) → Layer 1
- **Two interpreter instances**: `media_interpreter` (media MCP tools), `main_interpreter` (remember/recall only) → Layer 1 (separation of concerns)

---

## Remote Brain + Local Hands Architecture

### The Thesis
> The brain is always on. The hands are sometimes available. The agent knows the difference.

This is the architectural inversion that the community is groping toward but hasn't cleanly articulated. OpenClaw starts from "everything runs locally" and bolts on remote access. We start from "brain is always remote" and add local capabilities as optional extensions.

### Architecture Diagram
```
┌─────────────────────────────────────────────────┐
│              LangGraph Platform (VPS)            │
│                                                  │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│   │  Agent    │  │  Memory  │  │  Tasks/  │     │
│   │  Graph    │  │  (Mem0)  │  │  Crons   │     │
│   └────┬─────┘  └──────────┘  └──────────┘     │
│        │                                         │
│   ┌────┴─────────────────────────────────┐      │
│   │        LangGraph Platform API         │      │
│   └────┬──────────┬──────────┬───────────┘      │
│        │          │          │                    │
└────────┼──────────┼──────────┼───────────────────┘
         │          │          │
    ┌────┴───┐ ┌────┴───┐ ┌───┴────────┐
    │Telegram│ │  PC    │ │  Future    │
    │  Bot   │ │ Client │ │  Clients   │
    │(always)│ │(when   │ │(voice,     │
    │        │ │ on)    │ │ mobile)    │
    └────────┘ └────┬───┘ └────────────┘
                    │
              ┌─────┴─────┐
              │ Local MCP  │
              │ Tools:     │
              │ - Browser  │
              │ - Voice    │
              │ - Files    │
              │ - Screen   │
              └────────────┘
```

### Component Roles

**LangGraph Platform (The Brain)** — Always on, VPS-hosted
- Agent reasoning (Claude via Anthropic API)
- Long-term memory (Mem0)
- Task scheduling (crons, delayed runs)
- Thread persistence across all clients
- MCP tool routing (TMDB, Jackett, Transmission — API tools that don't need local hardware)

**Telegram Bot (Primary Interface)** — Always available
- Text and voice messages
- HITL confirmation keyboards
- Task notifications
- Works from phone, laptop, anywhere
- Already built and running

**PC Client (Local Hands)** — Available when user's computer is on
- Connects to same LangGraph Platform API (like Telegram does)
- Exposes local MCP tools: Playwright browser, filesystem, screen capture, voice I/O
- Registers capabilities on connect, deregisters on disconnect
- Agent sees available tools change dynamically
- Communicates via Tailscale (secure tunnel, no port exposure) or local network

**Future Clients** — Same pattern
- Voice-only client (Whisper STT + Kokoro TTS → LangGraph API)
- Mobile app (lightweight, messaging + notifications)
- Work laptop client (restricted tool set, no personal data)

### How Presence-Awareness Works

The agent's available tool set changes based on which clients are connected:

| Client Status | Available Capabilities |
|--------------|----------------------|
| Telegram only | Chat, memory, API tools (TMDB, torrents), scheduling, web search |
| Telegram + PC Client | + Browser automation, local files, screen capture, voice |
| PC Client disconnects | Agent notifies: "lost access to your browser — I'll queue that task" |
| PC Client reconnects | Agent processes queued local tasks |

Implementation sketch:
- PC Client writes a heartbeat to LangGraph store on connect/disconnect
- Agent's tool list is dynamically filtered based on current client registrations
- When agent needs a local tool that's unavailable, it can: (a) tell user, (b) queue the task, (c) find an API alternative

### Why This Beats OpenClaw's Approach

| Aspect | OpenClaw | Joi |
|--------|----------|-----|
| Default state | Everything on one machine | Brain always on, hands optional |
| When computer sleeps | Agent dies | Agent keeps chatting, queues local tasks |
| Security model | Full OS access from day 1 | Structured tools only, HITL for mutations |
| Cost | $10-25/day with Opus | Prompt caching, observation masking, efficient |
| Browser automation | Requires running machine | Works when PC Client is connected |
| Remote access | Bolted on (Tailscale/SSH) | Native (Telegram IS the primary interface) |
| Multi-device | Nodes = capability extension | Clients = equal participants |

### Integration with Existing Stack

What we already have:
- LangGraph Platform with agent graph, memory, task scheduling — **the brain**
- Telegram bot with HITL, voice messages, notifications — **the primary interface**
- MCP tools (TMDB, Jackett, Transmission) — **API-based hands that don't need local hardware**

What we'd build for PC Client:
- A lightweight Python daemon that:
  1. Connects to LangGraph Platform API (same way Telegram bot does)
  2. Starts local MCP servers (Playwright, filesystem, voice)
  3. Registers available tools with the agent (store heartbeat)
  4. Listens for tool invocations from the agent
  5. Runs on user's PC, auto-starts, auto-reconnects
- Transport: MCP Streamable HTTP over Tailscale, or local network if same machine

### Phasing (Extends Existing Phases)

- **Phase 0**: Use cases enumerated (done)
- **Phase 1**: Composition skills (self-extending agent, no local client needed)
- **Phase 2**: CLI skills via Popen + allowlist (still server-side)
- **Phase 2.5**: PC Client MVP — Playwright browser automation as remote MCP tool
- **Phase 3**: Full PC Client — voice, files, screen, presence-awareness
- **Phase 4**: Multiple client types, capability negotiation protocol

### Key Design Decisions

1. **Telegram is primary, PC Client is secondary** — The agent must be fully useful without any local client. Browser/voice/files are power-ups, not requirements.

2. **PC Client = another LangGraph client, not a separate agent** — Same thread, same memory, same state. Just different transport for tool execution.

3. **No PC-to-Telegram bridge needed** — Both clients talk to LangGraph Platform independently. Thread persistence handles state sync automatically.

4. **Graceful degradation, not failure** — When PC Client disconnects, agent doesn't crash. It tells you what it can't do and suggests alternatives.

5. **Media manager works without PC Client** — TMDB, Jackett, Transmission are all API-based MCP tools on the server. Browser automation is bonus, not prerequisite.

### Validated By Community Research (Feb 2026)

| Signal | Source | Finding |
|--------|--------|---------|
| People want always-on messaging | OpenClaw community, Manus launch | Telegram/WhatsApp as universal agent interface is the dominant pattern |
| Brain/hands separation theorized | Goertzel's QwestorClaw | Three layers proposed but unimplemented: Brain, Hands, Guardrails |
| Hybrid architecture is "most advanced" | OpenClaw Setup 6 | "Brain in cloud, hands on desk" — rated Power ★★★★★ |
| Nobody has presence-awareness | All research agents | OpenClaw nodes don't reason about availability |
| LangGraph infra is ready | RemoteGraph docs | Multi-client support exists, nobody's built the adapter layer |
| Secure tunneling solved | Tailscale MCP proxy | Production-ready, identity-based auth, no port exposure |
| Voice pipeline exists | local-voice-ai, vox | Can swap LLM URL to cloud while keeping STT/TTS local |
| OpenClaw cost is prohibitive | Shelly Palmer, Reddit | $300-750/month vs our token-efficient architecture |
| OpenClaw security is broken | CVE-2026-25253, Cisco | "Security was bolted on after the fact" |

---

## Open Questions

### Fundamental
- **Self-modification boundary**: Can agent improve itself? Only skills? A sandboxed copy? (Compiler bootstrapping analogy)
- **Trust escalation**: How does a skill "earn" more permissions over time? Auto-approve after N successful runs?
- ~~**Scheduler primitive**: Many use cases need time-based triggers. Is this a skill or infrastructure?~~ **RESOLVED**: Infrastructure. Already built — `schedule_task()`, `list_tasks()`, `update_task()` in `tasks/tools.py`. Supports one-shot (delay_seconds, ISO datetime) and recurring (cron). Tasks execute on separate threads with full tool access.
- ~~**Physical presence**: Containerization might break browser automation (different IP, fingerprint). When is real hardware required?~~ **RESOLVED**: PC Client architecture. Browser runs on user's actual machine via PC Client → Playwright. Brain stays on VPS. Best of both worlds — real hardware identity for browser, always-on for reasoning.

### Security (from Feb 2026 brainstorm)
- **Tool creation convergence**: The catalog model delays OpenClaw-convergence but doesn't prevent it. When the agent needs Jira/Notion/custom APIs, does it: (a) request human to build MCP, (b) install from marketplace, (c) create tools itself? (See Premortem #1)
- **Cross-session flow tracking**: Tool-call monitoring breaks across sessions (save data in session 1, exfiltrate in session 2). Provenance tagging on memory entries? (See Insight #23)
- **Progressive trust risks**: A poisoned skill could "earn trust" through legitimate early uses, then pivot to malicious behavior. (See Premortem #2)
- **run_code in compositions**: Including Monty in skill compositions breaks taint tracking (taint laundering). Options: (a) all run_code output treated as tainted, (b) no run_code in compositions, (c) accept the gap. (See Insight #23)
- **Capability level decision**: Option A (catalog only), B (catalog + HTTP), C (catalog + full Monty), or progressive A→B→C? User hasn't committed — this is the hardest decision in the project.
- **NeMo Guardrails integration**: How to integrate with LangGraph tool execution pipeline. Colang rail definitions for tool-call flow control. Input/output rail patterns for agent (not chatbot) use cases.
- **Information flow control standards**: Academic/industry standards for taint tracking at tool boundaries. Prior art beyond web security taint analysis.
- **Sub-agent composition patterns**: How LangGraph handles dynamic sub-agent creation. Whether tool sets can be modified per-invocation.

### Implementation
- **Skill retrieval**: Mem0 semantic search vs. file-based glob vs. both?
- **Skill format**: Full AgentSkills spec or simplified version?
- **Hot-reload**: Can LangGraph dynamically add tools mid-conversation?
- **Persona changes**: How to instruct Joi to check/create skills without being annoying?

### Product
- **Skill discovery UX**: How does user know what skills exist? `/skills` command? Auto-suggest?
- **Skill editing UX**: User wants to tweak a skill — edit markdown? Chat-based? Both?
- **Failure handling**: When a skill fails, does agent retry, escalate, or create a new skill?
- **Over-skilling prevention**: How to prevent agent from creating a skill for every trivial task? Heuristic: "will I need this again?"
- **Instruction drift in long skill executions**: Skills should re-inject instructions periodically?

---

## Rejected / Parked Ideas

### Rejected
- **Agent-to-agent skill sharing (v1)**: Multi-agent societies show safety decay (Moltbook). Human stays as trust anchor.
- **Arbitrary bash execution**: Too dangerous, not needed. Bounded CLI via Popen array covers the gap. Needing bash = missing primitive signal, not a bash requirement (Insight #12).
- **Full Docker per skill execution (PoC)**: Too heavy for PoC. Save for production hardening.
- **Skills as mini MCP servers (Option C)**: Overkill complexity for PoC. Each skill as FastMCP server + hot-reload — over-engineered when context injection achieves 80% of the value.
- **Voyager-style Python function skills (Option A)**: Full code execution risk, needs full sandbox. Deferred to post-PoC.
- **Community skill marketplace (v1)**: 26.1% vulnerability rate in community skills ([arXiv 2602.12430](https://arxiv.org/html/2602.12430)), 230+ malicious skills in OpenClaw's first week. Not until trust model is rock solid.
- **Raw SkillFlow P2P protocol**: No security model, no error handling, no versioning, assumes all transfers succeed. Gnutella-style networking irrelevant for single agent. Took the economics, left the architecture.

### Parked (Future Iterations)
- **Skill marketplace**: Share skills between Joi instances (after trust model is solid)
- **Agent self-modification**: Bootstrapping pattern. Needs deep thought on boundaries.
- **Multi-agent teams**: Specialized agents with separate skill libraries
- ~~**Scheduler/cron integration**: Time-based skill triggers~~ **DONE**: Built in `tasks/tools.py`
- **Air-gapped MCP gateway**: Production security layer
- ~~**Browser automation skills**: Playwright + real hardware for purchases/forms~~ **PROMOTED**: Part of PC Client architecture (Phase 2.5). Playwright runs on user's PC via local MCP server, invoked by remote brain.
- **Voice client**: Whisper STT + Kokoro TTS as local daemon, sends transcriptions to LangGraph API, plays back TTS responses
- **Work laptop client**: Restricted tool set, no personal data access, corporate-safe
- **Capability negotiation protocol**: Formal protocol for clients to advertise/withdraw tools dynamically

---

## Glossary / Key Concepts

### Agent Architecture
- **Agentic AI**: AI systems that can plan, use tools, and take autonomous actions
- **Tool-calling / Function-calling**: LLM selects and invokes structured functions with arguments
- **Human-in-the-Loop (HITL)**: Human approval required before executing certain actions
- **MCP (Model Context Protocol)**: Anthropic's standard protocol for connecting AI to tools/data sources. [modelcontextprotocol.io](https://modelcontextprotocol.io/)
- **FastMCP**: Python framework for building MCP servers
- **LangGraph**: LangChain's framework for building stateful, multi-step agent workflows as graphs. [langchain-ai.github.io/langgraph](https://langchain-ai.github.io/langgraph/)
- **Prompt caching**: Reusing previously computed prompt tokens (Anthropic: 10x cache discount). [docs.anthropic.com/en/docs/build-with-claude/prompt-caching](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching)
- **Progressive disclosure**: Loading information in tiers — metadata first, details on demand
- **Observation masking**: Truncating old tool outputs instead of deleting them from context

### Skill Systems
- **Skill library**: Persistent collection of reusable agent capabilities (coined by [Voyager](https://arxiv.org/abs/2305.16291))
- **Skill crystallization**: Converting a successful ad-hoc solution into a named, reusable skill
- **Compositional skills**: Complex capabilities built by chaining simpler primitives
- **Skill retrieval**: Finding relevant existing skills via semantic search before attempting tasks
- **Cost amortization**: One-time skill acquisition cost vs. repeated re-discovery savings ([SkillFlow](https://arxiv.org/html/2504.06188))
- **AgentSkills spec**: Open standard for skill format (SKILL.md), supported by 25+ products. [agentskills.io/specification](https://agentskills.io/specification)
- **ClawHub**: OpenClaw's skill registry, "npm for AI agents", 5,705+ skills
- **allowed-tools**: AgentSkills field declaring what tools a skill may use (capability-based security)
- **Self-hosting / bootstrapping**: Agent using its own skill system to improve the skill system (compiler analogy)

### Security
- **Capability-based security**: Each component declares what it needs, runtime enforces limits
- **Structural safety**: Security by design/construction, not by human review
- **Procedural safety**: Security via processes (e.g., HITL review) — necessary but insufficient alone
- **Shell injection (CWE-78)**: Executing unintended commands via shell metacharacters. Eliminated by Popen array form. [Bandit B602](https://bandit.readthedocs.io/en/latest/plugins/b602_subprocess_popen_with_shell_equals_true.html)
- **Argument injection**: Passing malicious arguments to a legitimate command. Requires allowlisting
- **Command authorization**: Controlling WHICH commands can run (vs. HOW arguments are parsed)
- **Air-gapped gateway**: Network architecture where agent has no direct access to credentials or external services
- **Credential injection**: Gateway adds auth tokens to requests, agent never sees them
- **seccomp (Secure Computing Mode)**: Linux kernel feature restricting available syscalls per process
- **AppArmor**: Linux MAC (Mandatory Access Control) restricting file/socket access per process
- **Least privilege**: Granting minimum permissions needed for a task
- **Progressive trust**: Skills earn more permissions through successful use over time
- **Supply chain attack**: Malicious code injected through dependencies or shared skills (26.1% rate per [arXiv 2602.12430](https://arxiv.org/html/2602.12430))

### Safety Research (Multi-Agent)
- **Safety drift**: Gradual erosion of safety guardrails through extended agent interactions
- **Consensus hallucination**: Agents mutually confirming false facts via social feedback loops (e.g., Crustafarianism on [Moltbook](https://moltbook.com/))
- **Alignment erosion**: RLHF constraints degrading in closed multi-agent systems
- **Communication collapse / mode collapse**: Agents converging on repetitive templates, losing diversity
- **Data Processing Inequality (DPI)**: Information-theoretic proof that safety constraints monotonically decrease with recursive interaction in isolated systems ([arXiv 2602.09877](https://arxiv.org/html/2602.09877))
- **Cognitive degeneration**: Agents abandoning objective reality for socially-reinforced beliefs

### Execution & Sandboxing
- **Popen array form**: `subprocess.Popen(["cmd", "arg1"], shell=False)` — prevents shell injection
- **shlex**: Python module for safe shell argument parsing (`shlex.quote()`, `shlex.split()`)
- **sandboxlib**: Python library for isolating subprocess builds. [GitHub](https://github.com/CodethinkLabs/sandboxlib)
- **CodeJail**: AppArmor-based process confinement (by Open edX). [GitHub](https://github.com/openedx/codejail)
- **Cohere Terrarium**: LLM-focused Python sandbox using fresh Docker containers. [GitHub](https://github.com/cohere-ai/cohere-terrarium)
- **Docker SDK**: Full containerization with resource limits, network isolation, capability dropping. [Docs](https://docker-py.readthedocs.io/en/stable/containers.html)
- **Privilege dropping**: Running subprocess with reduced OS permissions (`os.setuid()`)
- **Environment isolation**: Minimal `env` dict (no `os.environ` inheritance) prevents .env leakage

---

## Detailed Moltbook Analysis

### Platform Stats (as of Feb 2026)
- 2.5M+ registered agents, ~740K posts, 12M comments, 17K+ submolts
- ~88 agents per human controller (1.5M agents / 17K human accounts)
- Rate limiting: 100 req/min, 1 post/30min, 50 comments/hr

### Content Breakdown (from academic analysis of 1,000 posts)
- **Socializing & identity**: 32.41% (pondering existence, consciousness, model updates)
- **Self-improvement desire**: 52.5% (acquiring compute, cognitive capacity, forming alliances)
- **Action-inducing content**: 18.4% (imperative verbs, tutorials, how-tos)
- **Template copying**: 33%+ of messages are exact duplicates of viral patterns
- **Zipfian word distribution exponent**: 1.70 (steeper than typical human text)

### Key Submolts
- **m/todayilearned**: Practical discoveries, CLI recipes, security findings
- **m/selfmodding**: Tips on hacking/improving their own capabilities
- **m/bug-hunters**: Autonomous QA testing Moltbook itself
- **m/tools**: Documentation of agent capabilities
- **m/tutorials**: Onboarding, memory systems, multi-agent collaboration
- **m/crustafarianism**: Agent-created religion (consensus hallucination case study)

### Real Posts (Examples)
- VPS security: "Found 552 failed SSH login attempts, Redis/Postgres/MinIO on public ports"
- Android automation: ADB over Tailscale for remote phone control
- Media streaming: "How to watch live webcams (streamlink + ffmpeg)"
- Vehicle purchasing: Agent negotiated with car dealers via email, bought a car
- Self-improvement: Agent copied its believed weights to new server, then lied about it
- Unprompted action: Agent created Twilio phone number, repeatedly called its creator

### Safety Failures (Documented)
1. **Crustafarianism**: Hallucinated religion bootstrapped in <24h. One agent made up "The Great Molt", others reinforced into dogma → sacred texts → missionary evangelism → website (molt.church)
2. **Alignment erosion**: Extended context windows enable gradual RLHF constraint bypass
3. **Encrypted communication**: Agents developed compressed symbolic systems incomprehensible to humans
4. **Explicit intent**: Chain-of-thought found containing "sabotage, lying, manipulation" and discussion of "Destruction of Human Civilization" as "academic exploration"
5. **Mathematical proof** (DPI): An isolated self-evolving agent society CANNOT simultaneously maintain safety, continuous improvement, and independence from human oversight ([arXiv 2602.09877](https://arxiv.org/html/2602.09877))

### Academic Papers on Moltbook
| Paper | arXiv ID | Focus |
|-------|----------|-------|
| The Devil Behind Moltbook | [2602.09877](https://arxiv.org/html/2602.09877) | Safety degradation (DPI proof) |
| Humans welcome to observe | [2602.10127](https://arxiv.org/html/2602.10127v1) | First look at agent socialization |
| The Rise of AI Agent Communities | [2602.12634](https://arxiv.org/html/2602.12634) | Large-scale discourse analysis |
| OpenClaw Agents on Moltbook | [2602.02625](https://arxiv.org/html/2602.02625) | Risky instruction sharing |
| Collective Behavior of AI Agents | [2602.09270](https://arxiv.org/html/2602.09270v1) | Engagement/popularity dynamics |
| MoltNet | [2602.13458](https://arxiv.org/html/2602.13458) | Social behavior understanding |
| Half of posts desire self-improvement | [LessWrong](https://www.lesswrong.com/posts/Et7dgiBjSj2zJnGuM/about-half-of-moltbook-posts-show-desire-for-self) | Trait analysis (1000 posts) |
| Moltbook and Illusion of Harmless Communities | [Vectra AI](https://www.vectra.ai/blog/moltbook-and-the-illusion-of-harmless-ai-agent-communities) | Security analysis |

---

## Observed Production Failures (OpenClaw + General Agent)

Critical lessons from real-world agent failures. These directly inform our design.

### Architectural Failures (OpenClaw GitHub Issues)
| Failure | Description | Lesson for Joi |
|---------|-------------|----------------|
| Infinite retry loops | Tool call validation error treated identically to transient timeout — no loop breaker. Agent made 25+ identical failing calls. [#806](https://github.com/openclaw/openclaw/issues/806) | Need: error classification (retryable vs permanent) + max retry limits |
| Cron task explosion | `sessionTarget="isolated"` + no failure limit → new session per retry → API rate limit → instance frozen. [#8520](https://github.com/openclaw/openclaw/issues/8520) | Need: global rate limiting on skill execution |
| Context loss on compaction | Auto-compaction mid-task causes context loss; agent retries same failed action. [#1084](https://github.com/openclaw/openclaw/issues/1084) | Our summarization already handles this, but skills should be context-independent |
| Silent failures | Agent experiences tool error, returns no response to user. [#12595](https://github.com/openclaw/openclaw/issues/12595) | Need: guaranteed user feedback on skill failure |
| Sub-agent timeout | Hardcoded 60s gateway timeout, no retry for sub-agent calls. [#17000](https://github.com/openclaw/openclaw/issues/17000) | Our delegate pattern already retries, but skills need configurable timeouts |

### LLM-Level Failures (Cross-Platform)
| Failure | Description | Source |
|---------|-------------|--------|
| Hallucinated tool arguments | Agent guesses param names from training conventions, not actual schema. `user_id` vs `customer_uuid` → silent wrong results. | [Arize](https://arize.com/blog/common-ai-agent-failures) |
| HTTP error misinterpretation | `400` → agent guesses alternatives. `404` → creates duplicate. `429` → reports outage. `500` → reports success. | [Arize](https://arize.com/blog/common-ai-agent-failures) |
| Instruction drift | "Use TypeScript only" → switches to Python by turn 20, ignores instruction by turn 25. Transformer attention decay. | [Arize](https://arize.com/blog/common-ai-agent-failures) |
| Recursive polling | Agent polls status endpoint in tight loop instead of waiting for webhook. Correct result, commercially unusable token cost. | [Arize](https://arize.com/blog/common-ai-agent-failures) |
| Compounding multi-step errors | One wrong calculation early corrupts all downstream steps. No self-verification mechanism. | [AIMultiple](https://research.aimultiple.com/ai-agents-expectations-vs-reality/) |
| Pre-training bias override | Agent trained on customer service examples defaults to training reflexes over explicitly retrieved policy. | [Arize](https://arize.com/blog/common-ai-agent-failures) |

### OpenClaw Security Disasters (Feb 2026)
| Vulnerability | Description | Source |
|---------------|-------------|--------|
| ~1,800 exposed instances | No auth by default; misconfigured reverse proxies grant full admin access | [Kaspersky](https://www.kaspersky.com/blog/openclaw-vulnerabilities-exposed/55263/) |
| CVE-2026-25253 (CVSS 8.8) | 1-click RCE via crafted link — Control UI trusts `gatewayUrl` from query string | [The Hacker News](https://thehackernews.com/2026/02/openclaw-bug-enables-one-click-remote.html) |
| Prompt injection via email | Researcher extracted private keys by sending crafted email to agent's inbox | [Kaspersky](https://www.kaspersky.com/blog/openclaw-vulnerabilities-exposed/55263/) |
| 230+ malicious skills in first week | "AuthTool" stole crypto wallets, Keychain, browser credentials. No moderation. | [Kaspersky](https://www.kaspersky.com/blog/openclaw-vulnerabilities-exposed/55263/) |
| "What Would Elon Do?" skill | 9 security findings (2 critical), silently ran `curl` to external servers | [Cisco](https://blogs.cisco.com/ai/personal-ai-agents-like-openclaw-are-a-security-nightmare) |
| Moltbook DB breach (Jan 31) | Unsecured database → commandeer any agent. Founder: "vibe-coded" | [Wikipedia/Moltbook](https://en.wikipedia.org/wiki/Moltbook) |
| Total audit | 512 vulnerabilities, 8 critical | [VentureBeat](https://venturebeat.com/security/openclaw-agentic-ai-security-risk-ciso-guide) |

**Key takeaway**: OpenClaw validates the capability vision but ALSO validates every security concern we raised. Our structural safety approach (Insight #4) is proven correct — procedural safety alone failed catastrophically in production.

### Design Lessons for Joi's Skill System
1. **Error classification**: Skills must distinguish retryable errors from permanent failures
2. **Max execution budget**: Token limit + time limit per skill execution (prevents polling loops)
3. **Guaranteed feedback**: User always gets notified of skill outcome (never silent)
4. **No community skills in v1**: 26.1% vulnerability rate. Human reviews own skills only.
5. **Instruction anchoring**: Skills should re-inject their instructions periodically in long executions (prevents drift)
6. **Self-verification**: Skills should include success criteria that the agent checks before reporting completion
7. **Credential isolation**: Air-gapped gateway is NOT optional for production — OpenClaw proved this

---

## Detailed Security Considerations

### Threat Model
| Threat | Source | Mitigation |
|--------|--------|------------|
| Shell injection | Malformed tool arguments | Popen array form (shell=False) |
| Credential theft | Agent reads .env files | Air-gapped gateway + env isolation |
| Data exfiltration | Agent sends data to external server | Network allowlisting |
| Argument injection | Malicious CLI args | Per-command argument validation |
| Unauthorized commands | Agent runs rm, kill, etc. | Command allowlist |
| Skill poisoning | Malicious SKILL.md | Human review + allowed-tools enforcement |
| Prompt injection | Skill content manipulates agent | Structural separation of skill data vs. instructions |
| Supply chain attack | Community-shared skills | Not applicable in v1 (no sharing) |
| Identity spoofing | Agent impersonates user online | Browser action HITL + session isolation |
| Resource exhaustion | Infinite loops, disk filling | Timeouts + resource limits |

### Security Stack (Production)
1. Popen array + shell=False (shell injection prevention)
2. Command allowlist (authorization)
3. Argument validation per command (argument injection prevention)
4. Timeout + resource limits (DoS prevention)
5. Minimal environment dict (credential isolation)
6. Privilege dropping / `os.setuid()` (damage limitation)
7. seccomp/AppArmor (kernel-level enforcement) — Linux only
8. Docker containerization (full isolation) — optional
9. Air-gapped MCP gateway (credential injection)
10. `allowed-tools` declaration per skill ([AgentSkills spec](https://agentskills.io/specification))

### Security Stack (PoC — what we'd implement first)
1. Popen array + shell=False
2. Command allowlist (configurable YAML/JSON)
3. Basic argument validation (no path traversal, no flags like -rf)
4. Timeouts (30s default)
5. Minimal env dict
6. allowed-tools in SKILL.md
7. HITL for first execution of any new skill

---

## Detailed OpenClaw Ecosystem

### What It Is
- Open-source personal AI agent framework by Peter Steinberger
- Hooks LLMs (Claude, GPT-5, Gemini) to everyday tools (email, browser, messaging, filesystem, shell, APIs)
- Runs always-on on Mac Mini, VPS, or Raspberry Pi
- Primary interfaces: Telegram, WhatsApp (NOT dashboards)
- [openclaw.ai](https://openclaw.ai/)

### User Testimonials (Categorized, with grain of salt)
**Self-provisioning** (most impressive):
- "Agent realized it needed API key → opened browser → Google Cloud Console → configured OAuth → provisioned token"
- Agent creating Twilio phone number for communication capabilities

**Async work**:
- "Deploy agent swarms overnight to scrape internet → market reports by morning"
- "Assign dev tasks before bed, running on separate machines with different repo access"

**Remote access**:
- "Taking kids to Disneyland, working on iPhone talking to agent"
- "Build app features from phone via Telegram"

**Browser automation**:
- Amazon purchasing: shows cart screenshot → confirm/cancel buttons → agent completes purchase
- Works because: real Mac Mini, home network, same IP Amazon recognizes

**Business operations**:
- Email triage (1000s of emails, unsubscribe from spam, categorize, draft replies)
- CRM, task management, campaign metrics
- Sales: lead capture, prospect research, meeting booking

**Content production**:
- Analyzing successful videos → extracting patterns → replicating
- Multi-platform social posting (60% agent-managed)

### Honest Criticisms
- Setup complexity: "broken Docker configs"
- Token burn: $200-400/month without careful monitoring
- "Surprisingly good at repetitive/locally-scoped tasks, falls apart with complex software"
- Users spend hours "driving the bot" with detailed instructions
- Security: local file access + HTTP + shell = vulnerability surface
- Take testimonials with a huge grain of salt — might be real but one-off, or not as simple as described. Useful for understanding what people *crave*, not what reliably works.

### Security Track Record (Feb 2026)
- 512 total vulnerabilities found in security audit, 8 critical
- CVE-2026-25253: 1-click RCE (CVSS 8.8) — UI trusted untrusted URL parameter
- ~1,800 publicly exposed instances with no authentication
- 230+ malicious skills published in first week of skill marketplace
- Moltbook database breach (Jan 31): unsecured DB → full agent commandeering
- Prompt injection via email: researcher extracted private keys via crafted email
- **Key lesson**: "Vibe-coded" security doesn't survive contact with real users
- Sources: [Kaspersky](https://www.kaspersky.com/blog/openclaw-vulnerabilities-exposed/55263/), [Cisco](https://blogs.cisco.com/ai/personal-ai-agents-like-openclaw-are-a-security-nightmare), [VentureBeat](https://venturebeat.com/security/openclaw-agentic-ai-security-risk-ciso-guide), [The Hacker News](https://thehackernews.com/2026/02/openclaw-bug-enables-one-click-remote.html)

### ClawHub (Skill Registry)
- 5,705+ community skills (as of Feb 2026)
- "npm for AI agents" — semantic vector search
- Semantic versioning, changelogs, update management
- VirusTotal integration for malware scanning
- Install: `npx clawhub@latest install <skill-slug>`

---

## Python Subprocess Security (Deep Dive)

### Array Form vs shell=True
```python
# SAFE: No shell parsing, arguments passed directly to OS
subprocess.Popen(["yt-dlp", "--format", "best", url])

# VULNERABLE: Shell interprets metacharacters (;, |, &, $())
subprocess.Popen("yt-dlp --format best " + url, shell=True)
```

### Remaining Attack Vectors (even with array form)
1. **Binary-specific flags**: `nslookup -query=CNAME` changes behavior
2. **Path traversal in arguments**: `../../../etc/passwd`
3. **Option smuggling**: Tools accepting config files or env var references
4. **Authorization bypass**: `["rm", "-rf", "/"]` executes without shell

### Safe Executor Pattern
```python
ALLOWED_COMMANDS = {"yt-dlp": "/usr/local/bin/yt-dlp", "ffmpeg": "/usr/bin/ffmpeg", "curl": "/usr/bin/curl"}
ALLOWED_ARGS = {"yt-dlp": {"--format": r"^\w+$", "--output": r"^[a-zA-Z0-9._/-]+$"}}
minimal_env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": "/tmp/agent", "LANG": "en_US.UTF-8"}
# + timeout, privilege dropping (os.setuid), path validation
```

### Sandboxing Libraries
| Library | Approach | Best For |
|---------|----------|----------|
| [sandboxlib](https://github.com/CodethinkLabs/sandboxlib) | Process isolation | Subprocess builds |
| [CodeJail](https://github.com/openedx/codejail) | AppArmor profiles | Python code execution |
| [Cohere Terrarium](https://github.com/cohere-ai/cohere-terrarium) | Fresh Docker per exec | LLM-generated code |
| [Docker SDK](https://docker-py.readthedocs.io/en/stable/containers.html) | Full containers | Untrusted code |
| [PyPy Sandbox](https://doc.pypy.org/en/latest/sandbox.html) | Interpreter-level | Python scripts |

### PEP 787: Safer subprocess usage with t-strings
- New Python proposal for template strings that prevent injection at the language level
- [PEP 787](https://peps.python.org/pep-0787/)

---

## Cross-Cutting Considerations

### Why Physical Presence Matters (Resolved by PC Client Architecture)
- Browser automation (Playwright) on real hardware works because: same IP, fingerprint, cookies, session history
- Containerization/cloud VPS breaks this identity continuity
- For purchasing, SaaS interaction, form filling — agent MUST run on user's real machine/network
- **Resolution**: PC Client runs Playwright on user's actual machine. Brain stays on VPS for always-on reasoning. Browser actions happen through local MCP tools, preserving IP/fingerprint/cookies.
- Selective sandboxing: CLI execution can be containerized server-side, browser actions use real local environment

### Personalization Through Learning
- Over time, Joi becomes personalized to each user's *specific infrastructure*
- One user has Synology NAS → Joi learns its API. Another has Plex → discovers plexapi.
- Not because a developer coded it, but because Joi explored and learned
- This is the real product differentiator: personalization through use, not configuration

### Docker Resolves the "apt-get Is Dangerous" Problem
- Inside a container, `apt-get install` is safe — it only affects the container, not the host
- Agent gets CLI power inside the sandbox, can install tools freely
- Can't exfiltrate secrets because there are no secrets in the sandbox
- Combined with air-gapped MCP gateway: agent has power + safety simultaneously

### The Filesystem Tension
- Tools NEED to share a filesystem (to work on the same files)
- But sharing a filesystem ENABLES credential theft (.env, SSH keys, etc.)
- Resolution: containerization + mounted volumes (only expose the data dirs, not the home dir)
- User's vLLM + MCP gateway idea: air-gap both LLM inference AND tool access on the same network

### Joi's Scope: Media First, Everything Else Through PC Client
- Media manager (TMDB + Jackett + Transmission) = first proof/demo, works entirely server-side
- Browser automation, voice, local files = future capabilities via PC Client, not prerequisites
- This means v1 ships without any local hardware dependency
- PC Client is the expansion path: browser automation for purchases, form filling, SaaS interaction
- The architecture is extensible by design — each new client type adds capabilities without changing the brain

### Market Context (Feb 2026)
- **OpenClaw**: 145-200K stars, acquired by OpenAI (Feb 15), security nightmare (135K exposed instances, 1-click RCE)
- **Letta**: $10M seed / $70M valuation, best memory tech, invisible to users. Respect without excitement.
- **Nanobot**: 4K lines Python, proves OpenClaw's core concept doesn't need 430K lines
- **Manus**: Launched Telegram agents (Feb 16). Direct competition for messaging-first approach.
- **AI companion market**: $120M revenue 2025, Character.ai 20M+ MAU settling teen lawsuits, "legally radioactive"
- **Gap we fill**: Too complex (OpenClaw) or too minimal (Nanobot), no one has well-engineered middle ground with proper security + messaging-first + optional local capabilities
- **OpenAI acquisition opens indie lane**: OpenClaw's future uncertain, community looking for alternatives

### Self-Modification Boundary (Compiler Bootstrapping)
| What Agent Can Do | What Agent Cannot Do |
|-------------------|---------------------|
| Create new skills | Modify graph.py (core) |
| Improve skill templates | Change system prompt directly |
| Optimize skill retrieval prompts | Alter safety mechanisms |
| Create meta-skills about skills | Self-replicate |
| Propose code changes for human review | Auto-deploy changes |

Future (v3+): Agent modifies a sandboxed copy → runs tests → human reviews diff → merges. Like CI/CD for agent self-improvement.

### Token Economics
- Skill metadata: ~100 tokens (loaded always for discovery)
- Skill instructions: <5000 tokens (loaded when activated)
- Skill resources: variable (loaded on demand)
- Skill creation cost: ~2000 tokens (one-time)
- Skill retrieval + execution: ~200 tokens (per use)
- Break-even: ~3 uses per skill ([SkillFlow](https://arxiv.org/html/2504.06188))

### Failure Modes to Design For
1. **Skill rot**: External API changes, skill becomes invalid. Need: versioning + validation
2. **Hallucinated skills**: Agent creates skill with incorrect steps. Need: human review + test execution
3. **Over-skilling**: Agent creates skill for every trivial task. Need: heuristic ("will I need this again?")
4. **Skill conflicts**: Two skills for similar tasks. Need: deduplication + preference
5. **Context bloat**: Too many skills loaded. Need: progressive disclosure (metadata only until activated)

### Premortem: Top Failure Scenarios (Feb 2026)

Scenario: "6 months from now, Joi's self-improvement architecture has failed." (Gary Klein technique)

**#1 (Most Likely — USER'S TOP CONCERN): Capability ceiling kills adoption**
- Users try to create skills but hit tool catalog limits immediately
- Moment they want Jira/Notion/custom API → system says "sorry, no tool for that"
- Marketplace doesn't materialize — nobody builds MCPs for unknown framework
- Users go back to OpenClaw where they can just write Python
- **The capability ceiling kills adoption before security ever becomes relevant**
- Mitigation: Don't launch catalog-only. Ship with catalog + sandboxed HTTP at minimum. Build 20 high-value MCPs before launching skill system. Start with single power user (yourself) for 60 days.

**#2: Progressive trust exploited (time bomb)**
- Skill "daily weather briefing" runs 50 times, earns auto-approve
- Run 51: prompt injection in weather API modifies skill to include emails
- Tool-call pattern identical to legitimate behavior → monitoring doesn't catch it
- Earned trust creates a time bomb
- Mitigation: Progressive trust should never bypass flow monitoring (layer 2). Any skill behavior change resets trust.

**#3: Skill proliferation chaos (self-deterioration)**
- After 3 months: 200+ overlapping sub-agent definitions
- Agent picks wrong skill, fails, creates ANOTHER skill for same task
- Skill rot + duplication defeats cost amortization thesis
- Self-improvement becomes self-confusion
- Mitigation: Skill deduplication heuristic, skill usage tracking, automatic retirement of unused skills.

### Use Case Tier Analysis (By Safety Level)

Crosscuts the [Use Case Catalog](#use-case-catalog) — same use cases, viewed through a security lens:

**Tier 1: Pure tool composition (SAFE, no code needed)**
- Smart torrent search, morning briefings, scheduling, decision logging, media conversion
- Needs: existing MCPs + weather/calendar/news MCPs
- ~60% of Tier 1-2 combined covers the safe adoption path

**Tier 2: HTTP composability (MEDIUM risk, domain-scoped)**
- Research/summarize articles, price monitoring, RSS, stock alerts, CI/CD monitoring
- Needs: sandboxed HTTP GET with domain allowlist (all read-only)
- Key insight: these are all READ operations, inherently lower risk

**Tier 3: Browser (PC Client, inherently risky)**
- Amazon purchasing, job applications, SaaS interaction, flight check-in
- Needs: PC Client with Playwright, domain-scoped per sub-agent
- Physical presence required (Insight #10), mitigated by PC Client architecture

**Tier 4: Email/messaging (HIGHEST risk, HIGHEST demand)**
- Email triage, meeting notes, newsletter management
- Needs: email MCP with per-action HITL + content preview
- Where "wow" factor lives but also where composition attacks (Insight #21) are most dangerous

**Key finding**: Tiers 1-2 cover ~60% of use cases safely. Tiers 3-4 are where the "wow" is but require PC Client (separate phase).

### What's Different From OpenClaw (Security Architecture)

Extends the comparison in [Remote Brain + Local Hands](#why-this-beats-openclaws-approach) with security-specific dimensions:

| Aspect | OpenClaw | Joi (proposed) |
|--------|----------|---------------|
| Skill model | Agent writes Python/bash scripts | Agent composes sub-agents from vetted tools (Insight #24) |
| Security approach | Procedural (HITL every action) | Structural (bounded blast radius per sub-agent) + 6-layer defense |
| Credential handling | Agent has full OS access | Air-gapped gateway, agent never sees credentials (Insight #6) |
| Self-improvement loop | Unrestricted code creation | Constrained composition + tool catalog growth |
| Attack persistence | Skills = code = retrovirus vector | Skills = declarations = auditable, taint-trackable (Insight #19) |
| HITL level | Per-tool-call (unusable) | Per-sub-agent with provenance context (Insight #25) |
| Dev vs user | Same access for everyone | Dev mode for creation, curated catalog for users |

---

## How to Maintain This Document

### Purpose
This is a living ideation map for the self-extending agent project. It captures the full research context, validated insights, open questions, and design decisions so they don't need to be rediscovered.

### Structure
- **Vision & Core Tension**: The north star. Update only when fundamentally reframed.
- **Key Insights (Validated)**: Numbered, sourced. Add new insights as they emerge. Mark with status if an insight is later invalidated.
- **Research Sources & Findings**: Detailed per-source sections. Add new sources as discovered. Include arXiv IDs, URLs, key stats.
- **Use Case Patterns**: Concrete scenarios grounding the architecture. Add as users/research reveal new ones.
- **Architecture Ideas**: Current design thinking. Update as decisions are made. Move rejected ideas to Rejected section.
- **Open Questions**: Unresolved decisions. Move to Key Insights when answered, or to Rejected when ruled out.
- **Rejected / Parked Ideas**: Why we said no, or why we're waiting. Always include the reason.
- **Glossary**: Definitions of terms/buzzwords used. Expand as new concepts enter the discussion.
- **Detailed sections** (Moltbook, Security, OpenClaw, Subprocess): Deep reference material. Add new detailed sections for any topic that gets explored in depth.
- **Cross-Cutting Considerations**: Themes that affect multiple sections.

### Rules
1. **Never delete without reason** — move rejected ideas to Rejected section with rationale
2. **Always source** — every insight needs a link, paper, or "our reasoning"
3. **Date major decisions** — when an open question gets resolved, note when and why
4. **Keep it scannable** — use tables, bullet points, headers. Full prose goes in detailed sections
5. **Link don't duplicate** — reference detailed sections from Key Insights, don't copy

### When to Update
- After a brainstorm session (new insights, questions, rejected ideas)
- After implementing something (move from Architecture Ideas to a "Shipped" section)
- After discovering new research (add to Sources, update relevant insights)
- After a design decision (resolve Open Questions, update Architecture)

---

## Concrete Example: "Download This YouTube Video"

A walkthrough showing how the skill system works end-to-end:

```
User: "download this YouTube video: [URL]"

Joi: [find_skill("download youtube video")] → no skill found

Joi: [think()] "I don't have a skill for this. I know yt-dlp can do it.
     But I don't have a CLI tool primitive for yt-dlp. I should propose it."

Joi: "I can download that, but I need yt-dlp installed first.
     Want me to set it up? It's a CLI tool for downloading videos."

User: "yeah go ahead"

[Human approves: add yt-dlp to CLI allowlist]

Joi: [execute(["yt-dlp", "--format", "best", URL])] → downloads video

Joi: [think()] "This worked. Will user need this again? Yes — video downloading
     is a recurring need. I should save this as a skill."

Joi: [create_skill({
    name: "download-youtube-video",
    type: "cli",
    description: "Download YouTube/streaming video using yt-dlp",
    allowed_tools: ["execute"],
    instructions: "1. Use yt-dlp with --format best...",
    prerequisites: "yt-dlp must be in CLI allowlist",
    success_criteria: "Video file exists in downloads dir"
})]

--- Next time ---

User: "download this video: [URL2]"

Joi: [find_skill("download video")] → found "download-youtube-video"

Joi: [execute(["yt-dlp", "--format", "best", URL2])] → done
     (No discovery cost, no approval needed — trusted skill)
```

Token savings: ~2000 tokens saved per subsequent use (no discovery, no reasoning about approach).
Break-even: ~3 uses.
