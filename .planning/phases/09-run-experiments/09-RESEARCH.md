# Phase 9: Run Experiments - Research

**Researched:** 2026-02-20
**Domain:** Experiment execution — running Phase 8 harness with both tool variants, 3 runs each, producing per-run JSONL + LangSmith traces
**Confidence:** HIGH

## Summary

Phase 9 is an execution phase, not a build phase. The Phase 8 harness (`tests/experiment/test_experiment.py`) is fully operational — 40 test items (2 variants x 20 scenarios) with dual JSONL + LangSmith capture, zero assertions. Phase 9 adapts this harness for multi-run execution (3 runs per variant = 120 total LLM calls), per-variant per-run JSONL output files, automatic retry of transient failures, and partial rerun support.

The existing tooling is close to ready. `pytest-repeat` (v0.9.4, already installed) handles the `--count 3` repetition and exposes step numbers via the `__pytest_repeat_step_number` fixture. The main gaps are: (1) the `JSONLWriter` currently produces a single file per session — it needs to produce per-variant per-run files, (2) `pytest-rerunfailures` is NOT installed — needed for automatic retry, (3) LangSmith annotations need the run/rep number, and (4) a lightweight summary report after completion. All of these are small, targeted changes to existing infrastructure.

**Primary recommendation:** Modify `JSONLWriter` and `conftest.py` to emit per-variant per-run JSONL files (e.g., `results/baseline_run1.jsonl`). Add `pytest-rerunfailures` for automatic retry. Use `--count 3` for 3 runs. Add a summary conftest hook that prints scenario counts and timing after all runs complete. Run both variants sequentially (not parallel) — rate limits are not a concern at 120 total calls with Haiku.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Run both variants in parallel (unless LangSmith rate limits require sequential)
- 3 runs per variant to surface non-deterministic LLM behavior
- Low temperature (0.2-0.3) — slight variance for realistic behavior while staying mostly consistent
- pytest as the test runner (reuse Phase 8 experiment harness)
- Retry failed scenarios automatically — goal is clean data, not failure discovery
- Support rerunning a subset of scenarios (partial reruns) while retaining full history
- Per-run JSONL files (e.g., baseline_run1.jsonl, applike_run2.jsonl) — NOT consolidated
- Separate files enable partial reruns without losing prior data
- History must be retained so runs can be compared across time
- LangSmith traces annotated with variant and run ID for every scenario execution
- Run is complete when all scenarios in all runs have produced output
- No special validation beyond completeness — Phase 10 handles quality review

### Claude's Discretion
- Exact JSONL file naming convention and output directory structure
- Pytest fixtures and parametrization approach for multi-run execution
- Parallelization implementation (threading, subprocess, pytest-xdist, etc.)
- Whether to add a summary report after runs complete (scenario counts, timing)

### Deferred Ideas (OUT OF SCOPE)
None
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ANLS-01 | Clean experiment data collected on both tool variants with fixed pipeline | Phase 8 harness is verified complete (13/13 truths, 6/6 requirements). Phase 9 executes it 3x with per-run JSONL output. `--count 3` produces 120 items. `pytest-rerunfailures` retries transient API errors. Per-variant per-run JSONL files + LangSmith traces annotated with variant/run/rep metadata. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | 9.0.2 (installed) | Test runner, parametrization, `-k` selection | Already running Phase 8 harness. 40 items collected, verified. |
| pytest-repeat | 0.9.4 (installed) | `--count N` to repeat all tests N times | Already installed. `--count 3` produces 120 items with step IDs `1-3`, `2-3`, `3-3`. |
| pytest-rerunfailures | latest | `--reruns N` to auto-retry failed tests | NOT installed — must add via `uv add --dev pytest-rerunfailures`. Handles transient API timeouts/rate limits. |
| langchain-anthropic | (installed) | `ChatAnthropic.bind_tools().ainvoke()` | Direct model invocation. Already in test_experiment.py. |
| langsmith | (installed) | `@pytest.mark.langsmith`, `t.log_inputs/outputs/feedback` | Already integrated in test_experiment.py. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest-xdist | (NOT installed) | Parallel test execution across workers | NOT recommended — see Architecture Patterns below. Session-scoped fixtures + JSONL file handles get complicated with xdist workers. Sequential execution of 120 Haiku calls takes ~5-10 minutes, not worth the complexity. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `pytest-repeat --count 3` | Manual parametrize with `range(3)` | pytest-repeat already installed, produces clean step IDs, zero code change for repetition. Manual parametrize would duplicate what pytest-repeat does. **Use pytest-repeat.** |
| `pytest-rerunfailures --reruns 2` | `--lf` (last-failed) manual rerun | `--lf` requires manual intervention. `--reruns` is automatic within the same session. Goal is clean data without babysitting. **Use pytest-rerunfailures.** |
| Sequential execution | pytest-xdist parallel | 120 Haiku calls at ~1-2s each = 2-4 minutes sequential. xdist adds session fixture complexity. Anthropic Tier 1 = 50 RPM, which sequential easily fits. **Use sequential.** |

**Installation:**
```bash
uv add --dev pytest-rerunfailures
```

## Architecture Patterns

### Current State (Phase 8 Output)

```
tests/experiment/
├── conftest.py          # EVAL_MODEL, FIXED_TIMESTAMP, ZERO_PERSONA, run_id fixture, jsonl_writer fixture
├── capture.py           # JSONLWriter (single file per session)
├── scenarios.py         # 20 Scenario dataclasses
├── parity.py            # 7 parity tests
├── test_experiment.py   # Parametrized test: variant x scenario
└── variants/
    ├── registry.py      # ToolVariant, VARIANTS dict, register() decorator
    ├── baseline.py      # 3 tools
    └── applike.py       # 4 tools
```

### Changes Needed for Phase 9

```
tests/experiment/
├── conftest.py          # MODIFIED: add temperature param, rep number fixture, per-variant-run writers
├── capture.py           # MODIFIED: support per-variant per-run file naming
├── test_experiment.py   # MODIFIED: accept rep number, pass to writer + LangSmith annotations
└── (everything else unchanged)
```

### Pattern 1: Per-Variant Per-Run JSONL Files

**What:** Instead of one JSONL file per session, produce separate files per variant per run number.

**Naming convention recommendation:**
```
results/
├── baseline_run1_20260220_153000.jsonl
├── baseline_run2_20260220_153000.jsonl
├── baseline_run3_20260220_153000.jsonl
├── applike_run1_20260220_153000.jsonl
├── applike_run2_20260220_153000.jsonl
└── applike_run3_20260220_153000.jsonl
```

**Why this naming:** variant name + run number is human-readable and sortable. Timestamp suffix ensures partial reruns don't overwrite prior files. The locked decision says "history must be retained" — appending timestamps means old files persist.

**Implementation approach:**

The current `JSONLWriter` is session-scoped (one writer for all tests). For per-variant per-run files, there are two options:

**Option A: Writer factory in conftest (RECOMMENDED)**
Create a dictionary of writers keyed by `(variant_name, rep_number)`. The test requests the right writer based on its parameters. Writers are lazily created on first access.

```python
# conftest.py
class WriterPool:
    def __init__(self, run_id: str, git_commit: str, timestamp: str):
        self._writers: dict[tuple[str, int], JSONLWriter] = {}
        self._run_id = run_id
        self._git_commit = git_commit
        self._ts = timestamp

    def get(self, variant: str, rep: int) -> JSONLWriter:
        key = (variant, rep)
        if key not in self._writers:
            writer = JSONLWriter(
                run_id=self._run_id,
                git_commit=self._git_commit,
                filename=f"{variant}_run{rep}_{self._ts}.jsonl",
            )
            writer.write_metadata(...)
            self._writers[key] = writer
        return self._writers[key]

    def close_all(self):
        for w in self._writers.values():
            w.close()

@pytest.fixture(scope="session")
def writer_pool(run_id):
    pool = WriterPool(run_id, _git_commit(), _timestamp())
    yield pool
    pool.close_all()
```

**Option B: Modify JSONLWriter to accept filename** — simpler but requires more fixture changes.

Both work. Option A keeps the fixture interface cleaner.

### Pattern 2: Extracting Rep Number from pytest-repeat

**What:** `pytest-repeat` adds a `__pytest_repeat_step_number` fixture (0-indexed). The test needs this to tag JSONL lines and LangSmith annotations with the run number.

**Implementation:**
```python
# conftest.py
@pytest.fixture
def rep_number(request):
    """Extract 1-indexed repetition number from pytest-repeat, defaulting to 1."""
    marker = request.node.get_closest_marker("repeat")
    count = marker.args[0] if marker else request.config.option.count
    if count > 1:
        # pytest-repeat parametrizes __pytest_repeat_step_number as 0-indexed
        return request.node.callspec.params.get("__pytest_repeat_step_number", 0) + 1
    return 1
```

**Alternative simpler approach** — parse from the test node ID:
```python
@pytest.fixture
def rep_number(request):
    """Extract run number from pytest-repeat node ID (e.g., 'test_scenario[...-2-3]' -> 2)."""
    node_id = request.node.nodeid
    # When --count > 1, pytest-repeat appends '-{i+1}-{n}' to the node ID
    parts = node_id.rsplit("-", 2)
    if len(parts) >= 3:
        try:
            return int(parts[-2])
        except ValueError:
            pass
    return 1
```

The first approach is more robust as it reads from the actual parametrize data.

### Pattern 3: Temperature Configuration

**What:** Locked decision specifies temperature 0.2-0.3. Currently, test_experiment.py creates `ChatAnthropic` with default temperature (likely 1.0).

**Implementation:**
```python
EVAL_TEMPERATURE = 0.2  # Low temperature for mostly-consistent behavior with slight variance

llm = ChatAnthropic(
    model=EVAL_MODEL,
    api_key=settings.anthropic_api_key,
    temperature=EVAL_TEMPERATURE,
)
```

**Why 0.2 not 0.3:** Lower is better for reproducibility while still allowing the non-determinism the user wants to surface. The variance from 3 runs at temperature 0.2 is sufficient to reveal instability without adding noise.

### Pattern 4: Automatic Retry with pytest-rerunfailures

**What:** Transient API failures (rate limits, timeouts, network errors) should auto-retry, not fail the run.

**Configuration:**
```bash
# Run command
uv run pytest tests/experiment/test_experiment.py -m experiment --count 3 --reruns 2 --reruns-delay 5
```

- `--reruns 2`: Retry up to 2 times on failure
- `--reruns-delay 5`: Wait 5 seconds between retries (back off from rate limits)

**Interaction with pytest-repeat:** `--reruns` retries individual test items. `--count` repeats the entire test matrix. They compose correctly — a failed item in run 2 will retry within run 2, not spawn a new run.

**Alternative: configure in pyproject.toml:**
```toml
[tool.pytest.ini_options]
# Only for experiment runs — use CLI flag, not global config
```
Better to keep it as a CLI flag since it's experiment-specific, not global test config.

### Pattern 5: Partial Rerun Support

**What:** Rerun a subset of scenarios without losing prior data. Per-run files make this natural.

**How it works:**
- Old files in `results/` have timestamps, so new runs don't overwrite them
- `-k` flag selects subsets: `pytest -k "ambiguous" --count 3` reruns only ambiguous scenarios
- Per-variant per-run file naming with timestamp means new partial runs create new files
- All files coexist in `results/` for comparison

**Example commands:**
```bash
# Full run
uv run pytest tests/experiment/test_experiment.py -m experiment --count 3 --reruns 2 --reruns-delay 5

# Rerun only ambiguous scenarios (retains old files)
uv run pytest tests/experiment/test_experiment.py -m experiment --count 3 -k "ambiguous"

# Rerun one specific scenario for one variant
uv run pytest tests/experiment/test_experiment.py -m experiment --count 3 -k "ambiguous:vague_timing and baseline"
```

**History retention:** Since each run produces new timestamped files, all prior data is preserved. The `results/` directory accumulates files. Phase 10 can compare across timestamps.

### Pattern 6: Summary Report After Runs

**What:** A pytest session-finish hook that prints scenario counts, timing, and completion status.

**Implementation via conftest fixture or hook:**
```python
# conftest.py
def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Print experiment summary after all runs complete."""
    stats = terminalreporter.stats
    passed = len(stats.get("passed", []))
    failed = len(stats.get("failed", []))
    rerun = len(stats.get("rerun", []))
    duration = terminalreporter._session.testscollected  # approximate

    terminalreporter.section("Experiment Summary")
    terminalreporter.write_line(f"Passed: {passed}")
    terminalreporter.write_line(f"Failed: {failed}")
    terminalreporter.write_line(f"Rerun: {rerun}")
    terminalreporter.write_line(f"Total collected: {terminalreporter._session.testscollected}")
```

This is lightweight and built on pytest's hook system. No external dependencies.

### Anti-Patterns to Avoid

- **Running variants in separate pytest sessions:** This would create separate `run_id`s, making cross-variant comparison harder. Both variants in the same session share a `run_id`.
- **Using pytest-xdist for parallelism:** Session-scoped fixtures (JSONL writers) become complex with multiple workers. 120 Haiku calls take 2-4 minutes sequential — not worth the complexity.
- **Consolidated JSONL files:** Locked decision says per-run files. Don't consolidate.
- **Hardcoding --count in pyproject.toml:** Keep experiment-specific flags as CLI arguments, not global config.
- **Overwriting prior run files:** Timestamps in filenames ensure history retention. Never use fixed filenames like `baseline_run1.jsonl` without timestamps.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Repeat test N times | Custom loop or parametrize range | `pytest-repeat --count N` | Already installed, produces clean IDs, zero code needed for repetition |
| Retry transient failures | Custom try/except in test | `pytest-rerunfailures --reruns N --reruns-delay S` | Battle-tested plugin, handles all edge cases, reports rerun counts |
| Select test subsets | Custom filtering logic | `pytest -k "pattern"` | Built-in, composable with `and`/`or`/`not`, works with parametrize IDs |
| Summary report | Custom output script | `pytest_terminal_summary` hook | Native pytest hook, access to all test stats |
| Per-run timing | Manual timestamp tracking | `pytest --durations=10` | Built-in, shows slowest tests automatically |

**Key insight:** Phase 9 is an execution phase. Almost everything needed is a pytest invocation with the right flags. The code changes are minimal fixture/writer modifications.

## Common Pitfalls

### Pitfall 1: Session-Scoped JSONLWriter with pytest-repeat
**What goes wrong:** The current `jsonl_writer` is session-scoped — it creates one file. With `--count 3`, all 120 items write to the same file, violating the per-run file requirement.
**Why it happens:** Phase 8 assumed single-run execution.
**How to avoid:** Replace single `jsonl_writer` with a `WriterPool` that creates per-variant per-run files lazily. The test passes `(variant_name, rep_number)` to get the right writer.
**Warning signs:** All 120 lines in one JSONL file instead of 6 files (2 variants x 3 runs).

### Pitfall 2: Missing Temperature Setting
**What goes wrong:** Default temperature (1.0) produces highly variable responses across runs, making it impossible to distinguish real variant differences from random noise.
**Why it happens:** Phase 8 test_experiment.py doesn't set temperature on `ChatAnthropic`.
**How to avoid:** Add `temperature=0.2` to the `ChatAnthropic` constructor. Document it in the conftest constants alongside `EVAL_MODEL`.
**Warning signs:** Wild variation in responses across runs for the same scenario+variant.

### Pitfall 3: Rep Number Not in LangSmith Annotations
**What goes wrong:** LangSmith traces for run 1 and run 3 of the same scenario look identical — no way to distinguish them in the UI.
**Why it happens:** Phase 8 logs `run_id` but not the repetition number.
**How to avoid:** Add `rep` to `t.log_inputs()` and `t.log_feedback()`. This enables LangSmith filtering by rep number.
**Warning signs:** Can't filter LangSmith traces by run number.

### Pitfall 4: pytest-rerunfailures Interacts Badly with pytest-repeat Step Numbers
**What goes wrong:** If a test fails and is rerun by `pytest-rerunfailures`, the rerun might lose the `__pytest_repeat_step_number` context.
**Why it happens:** Both plugins parametrize tests. Their interaction isn't always clean.
**How to avoid:** Test the interaction before running the full experiment. Run `--count 2 --reruns 1` on a dummy test that intentionally fails once. Verify step numbers are preserved.
**Warning signs:** JSONL lines missing `rep` field or showing wrong rep numbers after retries.

### Pitfall 5: Rate Limit Cascade with --count 3
**What goes wrong:** 120 calls hit Anthropic rate limits (50 RPM on Tier 1), causing cascading failures that exhaust all `--reruns`.
**Why it happens:** pytest runs tests as fast as possible. 120 Haiku calls at ~1s each = 120 RPM if there's no latency.
**How to avoid:** Haiku responses typically take 1-3 seconds, naturally throttling to ~20-40 RPM. But if the model is fast, add a `time.sleep(0.5)` in the test or between runs. Monitor early — if the first 50 tests pass without rate limits, the rest will too.
**Warning signs:** Multiple `429 Too Many Requests` errors in the first minute.

### Pitfall 6: Partial Rerun Files Mixed with Full Run Files
**What goes wrong:** A partial rerun (e.g., only ambiguous scenarios) produces files with only 6 entries, mixed in `results/` with full-run files that have 20 entries. Analysis in Phase 10 confuses them.
**Why it happens:** Timestamped filenames are all in the same directory.
**How to avoid:** Two approaches: (a) include run type in filename (e.g., `baseline_run1_full_*.jsonl` vs `baseline_run1_partial_*.jsonl`), or (b) include the scenario filter in the JSONL metadata line. Option (b) is better — the metadata line already captures run context, just add a `filter` field. Phase 10 reads metadata to understand what each file contains.
**Warning signs:** Phase 10 reviewer assumes all files have all 20 scenarios.

## Code Examples

### Modified JSONLWriter for Per-Variant Per-Run Output
```python
# tests/experiment/capture.py
import json
from datetime import UTC, datetime
from pathlib import Path

RESULTS_DIR = Path("results")

class JSONLWriter:
    def __init__(self, run_id: str, git_commit: str, filename: str | None = None) -> None:
        self.run_id = run_id
        self.git_commit = git_commit
        RESULTS_DIR.mkdir(exist_ok=True)
        if filename:
            self._path = RESULTS_DIR / filename
        else:
            ts = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
            self._path = RESULTS_DIR / f"experiment_{run_id}_{ts}.jsonl"
        self._fh = self._path.open("a")  # append mode for crash safety

    def write_metadata(self, **kwargs) -> None:
        record = {
            "type": "run_metadata",
            "run_id": self.run_id,
            "git_commit": self.git_commit,
            "timestamp": datetime.now(tz=UTC).isoformat(),
            **kwargs,
        }
        self._fh.write(json.dumps(record) + "\n")
        self._fh.flush()

    def write_result(self, **kwargs) -> None:
        record = {
            "type": "scenario_result",
            "run_id": self.run_id,
            **kwargs,
        }
        self._fh.write(json.dumps(record) + "\n")
        self._fh.flush()

    def close(self) -> None:
        self._fh.close()
```

### WriterPool for Multi-File Management
```python
# tests/experiment/conftest.py (additions)
from tests.experiment.capture import JSONLWriter

EVAL_TEMPERATURE = 0.2

class WriterPool:
    """Lazily creates per-variant per-run JSONL writers."""

    def __init__(self, run_id: str, git_commit: str):
        self._writers: dict[tuple[str, int], JSONLWriter] = {}
        self._run_id = run_id
        self._git_commit = git_commit
        self._ts = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")

    def get(self, variant: str, rep: int) -> JSONLWriter:
        key = (variant, rep)
        if key not in self._writers:
            filename = f"{variant}_run{rep}_{self._ts}.jsonl"
            writer = JSONLWriter(
                run_id=self._run_id,
                git_commit=self._git_commit,
                filename=filename,
            )
            writer.write_metadata(
                model=EVAL_MODEL,
                temperature=EVAL_TEMPERATURE,
                fixed_timestamp=FIXED_TIMESTAMP,
                zero_persona=ZERO_PERSONA,
                variant=variant,
                rep=rep,
            )
            self._writers[key] = writer
        return self._writers[key]

    def close_all(self) -> None:
        for w in self._writers.values():
            w.close()

@pytest.fixture(scope="session")
def writer_pool(run_id: str):
    pool = WriterPool(run_id=run_id, git_commit=_git_commit())
    yield pool
    pool.close_all()
```

### Modified Test Function with Rep Number
```python
# tests/experiment/test_experiment.py
@pytest.mark.langsmith
@pytest.mark.experiment
@pytest.mark.asyncio
@pytest.mark.parametrize("variant_name", list(VARIANTS), ids=list(VARIANTS))
@pytest.mark.parametrize("scenario", SCENARIOS, ids=[s.id for s in SCENARIOS])
async def test_scenario(variant_name, scenario, run_id, writer_pool, rep_number):
    variant = VARIANTS[variant_name]
    llm = ChatAnthropic(
        model=EVAL_MODEL,
        api_key=settings.anthropic_api_key,
        temperature=EVAL_TEMPERATURE,
    )
    model = llm.bind_tools(variant.tools_factory())

    t.log_inputs({
        "prompt": scenario.prompt,
        "variant": variant_name,
        "category": scenario.category,
        "run_id": run_id,
        "rep": rep_number,
        "fixed_timestamp": FIXED_TIMESTAMP,
    })

    response = await model.ainvoke([
        SystemMessage(content=ZERO_PERSONA),
        HumanMessage(content=f"[{FIXED_TIMESTAMP}]\n{scenario.prompt}"),
    ])

    # ... content extraction (unchanged) ...

    t.log_outputs({"response_text": response_text, "tool_calls": tool_calls})
    t.log_feedback(key="variant", value=variant_name)
    t.log_feedback(key="run_id", value=run_id)
    t.log_feedback(key="rep", value=rep_number)

    writer = writer_pool.get(variant_name, rep_number)
    writer.write_result(
        variant=variant_name,
        scenario_id=scenario.id,
        category=scenario.category,
        prompt=scenario.prompt,
        response_text=response_text,
        tool_calls=tool_calls,
        input_tokens=usage.get("input_tokens", 0),
        output_tokens=usage.get("output_tokens", 0),
        total_tokens=usage.get("total_tokens", 0),
        rep=rep_number,
    )
```

### Run Commands

```bash
# Full experiment run: 3 reps, auto-retry
uv run pytest tests/experiment/test_experiment.py -m experiment \
    --count 3 --reruns 2 --reruns-delay 5 -v

# Partial rerun: only ambiguous scenarios
uv run pytest tests/experiment/test_experiment.py -m experiment \
    --count 3 --reruns 2 --reruns-delay 5 -k "ambiguous"

# Single scenario, single variant
uv run pytest tests/experiment/test_experiment.py -m experiment \
    -k "ambiguous:vague_timing and baseline"

# Dry run: verify collection without executing
uv run pytest tests/experiment/test_experiment.py -m experiment \
    --count 3 --collect-only
```

### Rep Number Fixture
```python
# tests/experiment/conftest.py
@pytest.fixture
def rep_number(request) -> int:
    """Extract 1-indexed repetition number from pytest-repeat."""
    count = request.config.option.count
    if count > 1:
        step = request.node.callspec.params.get("__pytest_repeat_step_number", 0)
        return step + 1
    return 1
```

## State of the Art

| Phase 8 State | Phase 9 Change | Why |
|---------------|---------------|-----|
| Single JSONL file per session | Per-variant per-run files with timestamps | Locked decision: per-run files for history retention |
| No repetitions | `--count 3` via pytest-repeat | 3 runs to surface non-deterministic behavior |
| No auto-retry | `--reruns 2 --reruns-delay 5` via pytest-rerunfailures | Goal is clean data, not failure discovery |
| Default temperature (~1.0) | `temperature=0.2` | Low temperature for consistent-but-slightly-varied behavior |
| No rep number in annotations | `rep` field in JSONL and LangSmith | Enables per-run filtering and comparison |
| No summary report | `pytest_terminal_summary` hook | Quick feedback on completion counts and timing |

## Open Questions

1. **Parallel vs sequential variant execution**
   - What we know: Locked decision says "run both variants in parallel (unless LangSmith rate limits require sequential)". Anthropic Tier 1 = 50 RPM. 120 sequential calls at ~1-3s each = 2-6 minutes. LangSmith SDK batches traces automatically, no rate limit concern.
   - What's unclear: Whether "parallel" means at the pytest level (xdist) or just "in the same session" (which is how pytest naturally interleaves parametrized tests).
   - Recommendation: Run in the same pytest session (natural interleaving of variants within a run). This satisfies "parallel" without xdist complexity. Both variants execute within each run, not as separate sequential blocks. If actual wall-clock parallelism is needed later, xdist can be added.

2. **Exact cost of 120 Haiku calls**
   - What we know: Claude Haiku 4.5 pricing: $0.80/MTok input, $4/MTok output. Each scenario has ~500 input tokens (system + timestamp + prompt) and ~100-200 output tokens. So 120 calls = ~60K input + ~18K output = ~$0.12.
   - What's unclear: Nothing — this is negligible.
   - Recommendation: Proceed without cost concerns.

3. **Whether `pytest-repeat` and `pytest-rerunfailures` interact correctly**
   - What we know: Both plugins use `pytest_generate_tests` and parametrization. In theory they compose (repeat handles repetition, rerunfailures handles retry). In practice, edge cases exist.
   - What's unclear: Whether a rerun preserves the correct rep number in the test ID and fixture data.
   - Recommendation: Test the interaction with `--count 2 --reruns 1` on a small subset before running the full 120-item suite. This is a Phase 9 implementation validation step, not a blocker.

## Sources

### Primary (HIGH confidence)
- `tests/experiment/test_experiment.py` — Existing harness code (read directly)
- `tests/experiment/conftest.py` — Session fixtures, constants (read directly)
- `tests/experiment/capture.py` — JSONLWriter implementation (read directly)
- `tests/experiment/scenarios.py` — 20 scenarios (read directly)
- `tests/experiment/variants/registry.py` — ToolVariant, VARIANTS (read directly)
- `pytest-repeat` source code — `__pytest_repeat_step_number` fixture, `make_progress_id`, parametrize integration (read directly from installed package)
- `pyproject.toml` — pytest markers, installed dependencies (read directly)
- `.planning/phases/08-experiment-harness/08-VERIFICATION.md` — Phase 8 verification (13/13 truths) (read directly)
- Context7 `/pytest-dev/pytest-rerunfailures` — `--reruns`, `--reruns-delay`, INI configuration
- Context7 `/pytest-dev/pytest-xdist` — Worker groups, session fixture with file locks, parallelism patterns

### Secondary (MEDIUM confidence)
- Context7 `/websites/pytest_en_stable` — `-k` filtering, parametrize, `pytest_terminal_summary`
- Context7 `/langchain-ai/langsmith-sdk` — `@traceable` metadata/tags, run filtering
- [Anthropic rate limits documentation](https://platform.claude.com/docs/en/api/rate-limits) — Tier 1: 50 RPM, token bucket algorithm
- [LangSmith rate limits](https://support.langchain.com/articles/8430904497-what-are-the-rate-limits-for-the-langsmith-api) — POST /runs/query 10req/10s, trace ingestion via SDK batching

### Tertiary (LOW confidence)
- None — all findings verified from codebase and official sources.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — pytest-repeat verified installed and tested with `--co`, pytest-rerunfailures API verified via Context7
- Architecture: HIGH — patterns derived from reading actual Phase 8 code and verifying pytest-repeat internals
- Pitfalls: HIGH — each pitfall based on direct code inspection (missing temperature, session-scoped writer, etc.)
- Execution estimates: MEDIUM — cost and timing estimates based on typical Haiku latency, not measured

**Research date:** 2026-02-20
**Valid until:** Indefinite (internal infrastructure, no external dependency drift)
