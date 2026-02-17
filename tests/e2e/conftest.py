import importlib.util
import sys
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio

_spec = importlib.util.spec_from_file_location("e2e", Path(__file__).parent.parent.parent / "scripts" / "e2e.py")
assert _spec and _spec.loader
_mod = importlib.util.module_from_spec(_spec)
sys.modules["e2e"] = _mod
_spec.loader.exec_module(_mod)
E2EHarness = _mod.E2EHarness  # type: ignore[attr-defined]


@pytest_asyncio.fixture
async def e2e():
    harness = E2EHarness()
    yield harness


@pytest.fixture
def fresh_user():
    return f"e2e-{uuid4().hex[:8]}"
