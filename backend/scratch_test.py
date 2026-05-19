import threading
from unittest.mock import patch, MagicMock

# Dummy QdrantClient for simulation
class QdrantClient:
    def __init__(self, url, timeout):
        self.url = url
        self.timeout = timeout
    def get_collections(self):
        return "real collections"

QDRANT_URL = "http://localhost:6333"

class ThreadSafeQdrantClient:
    def __init__(self):
        self._client = None
        self._last_class = None
        self._lock = threading.Lock()

    @property
    def client(self):
        if self._client is None or self._last_class is not QdrantClient:
            with self._lock:
                if self._client is None or self._last_class is not QdrantClient:
                    self._client = QdrantClient(url=QDRANT_URL, timeout=3)
                    self._last_class = QdrantClient
        return self._client

    def __getattr__(self, name):
        return getattr(self.client, name)

qclient = ThreadSafeQdrantClient()

# Simulating tests
@patch("__main__.QdrantClient")
def test_1(mock_qdrant):
    mock_inst = MagicMock()
    mock_inst.get_collections.return_value = "mock 1"
    mock_qdrant.return_value = mock_inst
    
    print("Test 1 Result:", qclient.get_collections())

@patch("__main__.QdrantClient")
def test_2(mock_qdrant):
    mock_inst = MagicMock()
    mock_inst.get_collections.return_value = "mock 2"
    mock_qdrant.return_value = mock_inst
    
    print("Test 2 Result:", qclient.get_collections())

def test_real():
    print("Real Result:", qclient.get_collections())

test_1()
test_2()
test_real()
