import os  # noqa: I001

from dotenv import load_dotenv

# Load .env FIRST so real credentials are available
load_dotenv()

# Only set defaults if .env didn't provide values (for VCR replay)
if not os.getenv("TMDB_API_KEY"):
    os.environ["TMDB_API_KEY"] = "dummy_key_for_vcr_replay"

import pytest  # noqa: E402
import tmdbsimple as tmdb  # noqa: E402

# Also set directly on module for modules already imported
if not tmdb.API_KEY:
    tmdb.API_KEY = os.environ["TMDB_API_KEY"]


@pytest.fixture(scope="module")
def vcr_config():
    return {
        "filter_query_parameters": ["api_key"],
        "filter_headers": ["authorization", "x-transmission-session-id"],
        "record_mode": "once",
    }


@pytest.fixture(autouse=True)
def reset_transmission_client():
    import joi_mcp.transmission as tm

    tm._client = None
    yield
    tm._client = None
