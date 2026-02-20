# Guardrails Research (Feb 2026)

## What Are Guardrails?

Programmable safety/validation layers that sit between your application and the LLM, intercepting inputs/outputs/tool-calls to enforce safety, topical, and behavioral constraints. Not optional — they're the primary enforcement mechanism (model training alone is insufficient).

## Architecture Patterns

### 1. Middleware / Chain-of-Responsibility (LangChain 1.0)
Hooks at distinct phases: `before_agent`, `before_model`, `after_model`, `after_agent`. Multiple guardrails stack in order.

### 2. Hook-Based (Snyk/Arcade Pattern)
Three HTTP webhook endpoints:
- `/access` — role-based tool availability
- `/pre` — validate/modify/block before tool runs
- `/post` — scan output, redact PII, block exfiltration

Standard HTTP POST, OpenAPI 3.0 schema. No proprietary SDKs.

### 3. Tripwire (OpenAI Agents SDK)
Parallel (default) or blocking mode. Guardrail returns `tripwire_triggered` boolean → raises exception immediately.

### 4. Sidecar (Snyk Evo)
Runtime sidecar in execution path. Sees agent decisions in real-time, can block/modify before completion.

### 5. Event-Driven (NeMo Guardrails)
Colang DSL defines event flows across 5 stages: input → dialog → retrieval → execution → output.

### 6. Graph Nodes (LangGraph Native)
Input/output guardrail nodes in the graph. Conditional routing for pass/fail. Most natural for LangGraph projects.

## The Five-Stage Pipeline

```
User Input → Input Rails → Dialog/Routing → [Retrieval Rails] → LLM → [Execution Rails] → Output Rails → Response
```

### Pre-Tool-Call Checks
| Check | Description |
|-------|-------------|
| Parameter validation | Schema + regex sanitization |
| Permission gating | RBAC, capability-based |
| Intent verification | AlignmentCheck — examines full CoT |
| Rate limiting | Token buckets, sliding windows |
| Input sanitization | PII redaction, credential scrubbing |
| Scope enforcement | Enum constraints, allowlists |
| Dry-run validation | Simulation mode, human approval |

### Post-Tool-Call Checks
| Check | Description |
|-------|-------------|
| Output sanitization | Prompt injection pattern scanning |
| PII masking | Presidio, regex-based scrubbing |
| Data exfiltration blocking | Egress monitoring, domain filtering |
| Result validation | JSON Schema, type checking |
| Code security scanning | CodeShield — 50+ CWEs, 8 languages |
| Behavioral drift | AlignmentCheck CoT auditing |

## Framework Comparison

| Framework | Type | Approach | Best For | Cost |
|-----------|------|----------|----------|------|
| **NeMo Guardrails** | OSS (NVIDIA) | Full conversation engine, Colang DSL, 5-stage pipeline | Enterprise conversational AI with flow control | Free (library); NIM models need GPU |
| **Guardrails AI** | OSS | I/O validation, Pydantic, composable validators | Output validation, structured data, safety | Free (+ LLM costs for ML validators) |
| **LlamaFirewall** | OSS (Meta) | 3 scanners: PromptGuard2 + AlignmentCheck + CodeShield | Combined defense (1.75% ASR from 17.6%) | Free |
| **LlamaGuard** | OSS (Meta) | Fine-tuned Llama for safety classification, 14 categories | Content safety at scale | Free (self-hosted GPU) |
| **Lakera Guard** | Commercial API | Real-time LLM firewall, 95.22% detection accuracy | Production prompt injection defense | Freemium |
| **AWS Bedrock Guardrails** | Managed | Content filters, denied topics, PII, contextual grounding | AWS shops, pay-per-use | $0.15/1K text units |

## NeMo Guardrails Deep Dive

**v0.20.0** (Jan 2026), 5.7k stars, ThoughtWorks "Adopt" rating.

### Core Concepts
- **Colang** — DSL for defining conversational flows. v1.0 (stable, `define` keyword), v2.0 (Python-like, stateful, parallel flows — but incomplete, can't use Guardrails Library yet)
- **5 rail types**: input, dialog, retrieval, execution, output
- **LLM-powered CoT**: `generate_user_intent()` → `generate_next_step()` → `generate_bot_message()` (3 LLM calls per message in default mode; single-call mode available)

### NemoGuard NIMs (GPU microservices)
| NIM | Model |
|-----|-------|
| Content Safety | Llama 3.1 NemoGuard 8B, 42 hazard categories |
| Topic Control | Predefined topical boundaries |
| Jailbreak Detection | Trained on 17k known jailbreaks |

### Strengths
- Most comprehensive OSS guardrails framework
- Parallel rail execution (since v0.15)
- OpenTelemetry built-in, multimodal (v0.20)
- LangGraph integration via `RunnableRails(config, passthrough=True)`

### Weaknesses
- 100-500ms latency overhead per request
- Official docs still say "beta, not recommended for production" (despite ThoughtWorks Adopt)
- **Tool messages bypass input rails** — output rails are the only defense
- LangGraph streaming degraded (single large chunks, no token-level)
- Colang 2.0 incomplete

### LangGraph Integration
```python
from nemoguardrails import RailsConfig
from nemoguardrails.integrations.langchain import RunnableRails

config = RailsConfig.from_path("./config")
guardrails = RunnableRails(config, passthrough=True, verbose=True)
guarded_chain = prompt | (guardrails | model_with_tools)
```

## Guardrails AI Deep Dive

**v0.9.0** (Feb 2026), 6.4k stars, 67 Hub validators.

### Core Pattern
```python
from guardrails import Guard, OnFailAction
from guardrails.hub import ToxicLanguage, DetectJailbreak, CompetitorCheck

guard = Guard().use_many(
    ToxicLanguage(threshold=0.5, on_fail=OnFailAction.EXCEPTION),
    DetectJailbreak(on_fail=OnFailAction.EXCEPTION),
    CompetitorCheck(["Apple", "Microsoft"], on_fail=OnFailAction.FIX),
)
res = guard(model="gpt-4o", messages=[...])
```

### OnFail Actions
`NOOP` | `FIX` | `FILTER` | `REFRAIN` | `EXCEPTION` | `FIX_REASK`

### LangGraph Pattern (Graph Nodes)
```python
def input_guardrails(state):
    guard = Guard().use_many(
        ToxicLanguage(threshold=0.5, on_fail="exception"),
        DetectJailbreak(on_fail="exception"),
    )
    try:
        result = guard.validate(state["messages"][-1].content)
        return {}
    except Exception:
        return {"end": True, "response": "Blocked by guardrails"}

# Wire: START → input_guard → model → output_guard → END
```

### Key Hub Validators
- **Safety**: ToxicLanguage, NSFWText, ProfanityFree, MentionsDrugs
- **Security**: DetectJailbreak, UnusualPrompt, SecretsPresent, ExcludeSQLPredicates
- **PII**: DetectPII (Presidio), GuardrailsPII
- **Factuality**: BespokeMiniCheck, ProvenanceLLM, GroundedAIHallucination
- **Format**: ValidJSON, ValidSQL, ValidPython, RegexMatch
- **Domain**: CompetitorCheck, RestrictToTopic, BiasCheck, ReadingLevel

### Server Mode
OpenAI-compatible endpoint. Deploy as standalone HTTP service, decouple from app code.

## LlamaFirewall (Meta, May 2025)

Three-scanner architecture with **combined 1.75% attack success rate** (90% reduction):

| Scanner | Phase | What It Does |
|---------|-------|-------------|
| PromptGuard 2 (86M/22M params) | Input | Jailbreak detection, 98% AUC, 19.3ms latency |
| AlignmentCheck | Reasoning | Chain-of-thought auditor — detects goal hijacking |
| CodeShield | Output | Static analysis, 50+ CWEs across 8 languages |

Plugin-based like Snort/YARA — community-built rules. **AlignmentCheck is frontier** — audits reasoning, not just messages.

## Enterprise Platforms

| Feature | AWS Bedrock | Azure AI Foundry | Google Vertex | NVIDIA Stack |
|---------|-------------|------------------|---------------|--------------|
| Runtime cost | $0.0895/vCPU-hr | Pay for compute | $0.00994/vCPU-hr | $4,500/GPU/yr |
| Framework lock-in | None | Microsoft-native | Google ADK | None |
| Guardrails | Managed (content, PII, grounding) | Content Safety API | Gemini safety filters | NeMo (OSS) |
| Multi-agent | A2A protocol | A2A + MCP | A2A + MCP | MCP |

### AWS Bedrock Guardrails (standout managed solution)
- Content Filters (6 categories, configurable strength)
- Denied Topics (up to 30, ML-based, not keyword)
- PII Filters (**free** — detect or anonymize)
- Contextual Grounding (hallucination detection against source docs — **unique to AWS**)
- $0.15/1K text units after 85% price reduction (Dec 2024)

### NVIDIA Agent Stack (clarified naming)
- "AgentCore" = **Amazon Bedrock** product, NOT NVIDIA
- NVIDIA's agent orchestration = **NeMo Agent Toolkit** (formerly AgentIQ)
- Open-source (Apache 2.0), framework-agnostic, MCP support, profiling/observability

## Industrial Standards

### OWASP LLM Top 10 (2025)
LLM01 Prompt Injection | LLM02 Sensitive Info Disclosure | LLM03 Supply Chain | LLM04 Data Poisoning | LLM05 Improper Output Handling | LLM06 Excessive Agency | LLM07 System Prompt Leakage | LLM08 Vector/Embedding Weaknesses | LLM09 Misinformation | LLM10 Unbounded Consumption

### Key Standards
- **NIST AI RMF** (AI 100-1, Mar 2025) — Govern/Map/Measure/Manage framework
- **EU AI Act** — Full application Aug 2, 2026. Up to EUR 35M or 7% global turnover penalties
- **ISO/IEC 42001:2023** — First AI management system standard (PDCA methodology)

### Provider Consensus
- **Defense-in-depth** — never rely on single layer
- **Security controls must NOT be delegated to LLM** via system prompt — enforce at infrastructure level
- **Human-in-the-loop for mutations** — require approval for write operations
- **AlignmentCheck-style reasoning auditing** is the frontier
- Anthropic leads safety (C+ grade in 2025 AI Safety Index)

## Key Statistics
| Metric | Value |
|--------|-------|
| Simple prompt attacks causing incidents | 35% (Adversa AI 2025) |
| Constitutional Classifiers jailbreak success | 4.4% |
| LlamaFirewall combined ASR | 1.75% |
| NeMo threat detection rate | 80% |
| NeMo false positives | 62 per 1,000 |
| Lakera detection accuracy | 95.22% |
| PromptGuard 2 latency | 19.3ms |

## Relevance to Our Project (Joi Agent)

### What We Already Have
- HITL via `interrupt_on` for mutation tools (add/remove/pause/resume torrent)
- Anthropic Claude with built-in safety training

### Recommended Approach (Lightweight → Full)

**Phase 1 — Native LangGraph (free, zero deps)**
- Input/output validation graph nodes
- Tool parameter validation before execution
- PII detection in outputs (Presidio)
- We already have HITL for mutations — extend to broader tool categories

**Phase 2 — Guardrails AI (free, light deps)**
- Add `Guard` nodes with Hub validators (ToxicLanguage, DetectJailbreak, DetectPII)
- Structured output validation via Pydantic
- Streaming compatible
- `.to_runnable()` for LCEL, or graph node pattern for LangGraph

**Phase 3 — NeMo Guardrails (if needed)**
- Full dialog flow control via Colang
- Topic control rails
- Retrieval rails for future RAG
- Trade-off: streaming degraded, 100-500ms latency

**Skip unless cloud-deployed:**
- AWS Bedrock Guardrails (managed, pay-per-use)
- NVIDIA NIM guardrail models (need GPUs)

### Key Decision: Where guardrails live
```
Option A: Graph nodes (native LangGraph)
  + Full control, streaming preserved, zero deps
  - Manual implementation of each check

Option B: Middleware wrapper (NeMo/Guardrails AI)
  + Declarative, rich ecosystem
  - Streaming degraded, latency overhead, coupling

Option C: Sidecar service (Guardrails AI server mode)
  + Decoupled, language-agnostic, scalable
  - Extra infra, network latency

Recommendation: Option A for core + Option B selectively for validators
```
