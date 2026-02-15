# TODO

## Joi Response Style
Joi answers in multiple lines/paragraphs. Real humans text in short bursts, not essays. Need to tune persona/system prompt to produce conversational single-line replies.

## MCP Data Format for Interpreter
Outside interpreter: CSV/TSV works great — LLM parses it natively. Inside interpreter (code execution): need structured format (JSON or list-of-lists) so generated code can reference fields by name/index without fragile string parsing. Decide on format and branch MCP output based on caller context.

## Torrent Search: Cyrillic/Transliteration Problem
"Interstellar" not found because Jackett results use Russian names. Agent passes English filter expression. Even Russian titles may be transliterated to Latin with dots instead of spaces (e.g. `Интерстеллар` → `Interstellar` or `I.n.t.e.r.s.t.e.l.l.a.r`). Need fuzzy/normalized matching — possibly strip dots, lowercase, and do substring match instead of exact JMESPath filter.
