# Serega

Joi companion agent with MCP integration.

## Dev Workflow

MCP server (Terminal 1): `make dev-mcp`
Agent (Terminal 2): `make dev-agent`

Both auto-reload on source changes.

## Testing

Contract tests use VCR cassettes for HTTP replay.

Run tests: `uv run pytest -v -m contract`
Refresh cassettes: `uv run pytest -v -m contract --record-mode=all`

## Persona Design

### Techniques Used

**PList/Parenthetical Format**
Dense attribute encoding: `[into: cinema, Zemfira, Witcher3]` instead of prose paragraphs.

**Ali:Chat Dialogue Examples**
Show personality through brief exchanges rather than describing traits:
```
*not looking up* oh you're here. cool I guess
ugh why do I even... *helps anyway*
```

**Bracket Tagging**
Compact lists for traits, interests, sounds:
```
[hates: cilantro, small-talk, horror-films]
[RU-sounds: ахахах, пфф | блин, бля]
```

**Placement Hierarchy**
Critical behavioral rules (tools, time awareness) at bottom - highest LLM attention weight.

**Extractive Compression**
Select important phrases verbatim, remove filler. Don't paraphrase - extract.

### Results
- 155 lines → 44 lines (71% reduction)
- ~5600 chars → ~1900 chars (66% reduction)
- Core personality intact, derivable details eliminated

### Resources
- [kingbri's Minimalistic Character Guide](https://rentry.co/kingbri-chara-guide) - PList format, 600 token target
- [Ali:Chat Guide](https://rentry.co/alichat) - dialogue-as-formatting technique
- [SillyTavern Character Design](https://docs.sillytavern.app/usage/core-concepts/characterdesign/) - token budgeting
- [LLMLingua](https://llmlingua.com/) - extractive prompt compression research

### Token Budget
Every token in persona = less memory for conversation history. 1000-token persona on 2048 context = only ~3 exchanges remembered.
