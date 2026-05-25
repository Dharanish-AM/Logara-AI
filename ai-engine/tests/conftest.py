"""
Shared test fixtures and configuration for the ai-engine test suite.

The key challenge is that SearchService and the lifespan hook both call
get_embedding_model() which would download ~90 MB on first run. The autouse
fixture below pre-sets the lazy-loaded module globals to MagicMocks so the
real SentenceTransformer and QdrantClient constructors are never called.
"""
import pytest
from unittest.mock import MagicMock

import services.search as search_module


@pytest.fixture(autouse=True)
def mock_lazy_globals():
    """
    Pre-populate the module-level lazy singletons with mocks before each
    test so that get_embedding_model() and get_qdrant_client() short-circuit
    without touching the network or filesystem.
    """
    original_model = search_module._embedding_model
    original_client = search_module._qdrant_client

    search_module._embedding_model = MagicMock()
    search_module._qdrant_client = MagicMock()

    yield

    # Restore originals so tests don't bleed state into each other
    search_module._embedding_model = original_model
    search_module._qdrant_client = original_client
