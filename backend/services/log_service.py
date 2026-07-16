import os
import uuid
import logging
import hashlib
from typing import List, Dict, Any, Optional, Tuple

import httpx
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from qdrant_client.http.models import PointStruct

from utils.constants import (
    SCHEMA_TIMESTAMP,
    SCHEMA_LEVEL,
    SCHEMA_MESSAGE,
    SCHEMA_METADATA,
    SCHEMA_PARSER_TYPE,
    SCHEMA_RAW,
)

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
LOCAL_LLM_MODEL = os.getenv("LOCAL_LLM_MODEL", "llama3")
QDRANT_COLLECTION = "logs"
VECTOR_SIZE = 384


class LogService:
    def __init__(self, qclient: QdrantClient):
        self.qclient = qclient
        self._collection_verified = False

    def _ensure_collection(self):
        """
        Create the Qdrant collection if it does not already exist.
        """
        if self._collection_verified:
            return
        try:
            collections = self.qclient.get_collections().collections
            collection_names = [c.name for c in collections]
            if QDRANT_COLLECTION not in collection_names:
                self.qclient.create_collection(
                    collection_name=QDRANT_COLLECTION,
                    vectors_config=qmodels.VectorParams(
                        size=VECTOR_SIZE,
                        distance=qmodels.Distance.COSINE
                    ),
                )
                logger.info(f"Created Qdrant collection '{QDRANT_COLLECTION}'.")
            self._collection_verified = True
        except Exception as e:
            logger.debug(f"Failed to verify/create Qdrant collection: {e}")


    def get_embedding(self, text: str) -> List[float]:
        """
        Generate vector embedding using local Ollama service.
        Falls back to a deterministic hash-based mock vector if Ollama is unreachable.
        """
        try:
            url = f"{OLLAMA_BASE_URL}/api/embeddings"
            response = httpx.post(
                url,
                json={"model": LOCAL_LLM_MODEL, "prompt": text},
                timeout=5.0
            )
            if response.status_code == 200:
                emb = response.json().get("embedding")
                if isinstance(emb, list) and len(emb) > 0:
                    # Adjust dimensions if necessary to match VECTOR_SIZE
                    if len(emb) != VECTOR_SIZE:
                        if len(emb) > VECTOR_SIZE:
                            emb = emb[:VECTOR_SIZE]
                        else:
                            emb = emb + [0.0] * (VECTOR_SIZE - len(emb))
                    return emb
        except Exception as e:
            logger.debug(f"Ollama embedding lookup failed: {e}. Using deterministic mock vector.")

        # Deterministic mock fallback
        h = hashlib.sha256(text.encode('utf-8')).digest()
        mock_vec = []
        for i in range(VECTOR_SIZE):
            val = (h[i % len(h)] / 127.5) - 1.0
            mock_vec.append(val)
        return mock_vec

    def store_log(self, parsed_log: Dict[str, Any], raw_log: str) -> str:
        """
        Vectorize and store a parsed log payload directly into Qdrant.
        """
        log_id = str(uuid.uuid4())
        message = parsed_log.get(SCHEMA_MESSAGE, "")
        vector = self.get_embedding(message)

        metadata = parsed_log.get(SCHEMA_METADATA, {}) or {}
        service_id = metadata.get("service") or metadata.get("service.name") or "unknown_service"

        payload = {
            "id": log_id,
            SCHEMA_TIMESTAMP: parsed_log.get(SCHEMA_TIMESTAMP),
            SCHEMA_LEVEL: parsed_log.get(SCHEMA_LEVEL, "INFO").upper(),
            SCHEMA_MESSAGE: message,
            SCHEMA_PARSER_TYPE: parsed_log.get(SCHEMA_PARSER_TYPE),
            SCHEMA_RAW: raw_log,
            SCHEMA_METADATA: metadata,
            "service_id": service_id
        }

        point = PointStruct(
            id=log_id,
            vector=vector,
            payload=payload
        )

        self._ensure_collection()
        self.qclient.upsert(
            collection_name=QDRANT_COLLECTION,
            points=[point]
        )
        return log_id

    def get_logs(
        self,
        page: int = 1,
        limit: int = 10,
        level: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Retrieve, filter, and paginate logs with timestamp-based sorting.
        """
        filter_conditions = []

        if level:
            filter_conditions.append(
                qmodels.FieldCondition(
                    key=SCHEMA_LEVEL,
                    match=qmodels.MatchValue(value=level.upper())
                )
            )

        if start_time or end_time:
            range_cond = qmodels.Range()
            if start_time:
                range_cond.gte = start_time
            if end_time:
                range_cond.lte = end_time
            filter_conditions.append(
                qmodels.FieldCondition(
                    key=SCHEMA_TIMESTAMP,
                    range=range_cond
                )
            )

        scroll_filter = qmodels.Filter(must=filter_conditions) if filter_conditions else None

        # Fetch up to a large threshold for sorting in memory to guarantee chronologically accurate pages
        # scroll returns Tuple[List[Record], Optional[PointId]]
        self._ensure_collection()
        records, _ = self.qclient.scroll(
            collection_name=QDRANT_COLLECTION,
            scroll_filter=scroll_filter,
            limit=5000,
            with_payload=True,
            with_vectors=False
        )
        logs = []
        for r in records:
            if r.payload:
                p = dict(r.payload)
                p["id"] = str(r.id)
                logs.append(p)

        # Sort descending by timestamp
        def get_ts(log):
            return log.get(SCHEMA_TIMESTAMP) or ""

        sorted_logs = sorted(logs, key=get_ts, reverse=True)

        total = len(sorted_logs)
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_logs = sorted_logs[start_idx:end_idx]

        return paginated_logs, total

    def semantic_search(self, query: str, limit: int = 5) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """
        Perform vector similarity search on logs and use Ollama to synthesize an answer.
        """
        if limit < 1 or limit > 50:
            raise ValueError("Result limit must be between 1 and 50")

        self._ensure_collection()
        query_vector = self.get_embedding(query)

        search_fn = getattr(self.qclient, "search", None)
        if callable(search_fn):
            results = search_fn(
                collection_name=QDRANT_COLLECTION,
                query_vector=query_vector,
                limit=limit,
                with_payload=True
            )
        else:
            res = self.qclient.query_points(
                collection_name=QDRANT_COLLECTION,
                query=query_vector,
                limit=limit,
                with_payload=True
            )
            results = res.points if hasattr(res, "points") else res
        logs = []
        for r in results:
            if r.payload:
                p = dict(r.payload)
                p["id"] = str(r.id)
                logs.append(p)

        # If we have no logs, we return empty list and message
        if not logs:
            return [], "No matching logs found."

        # Attempt to synthesize natural language query response using Ollama
        answer = None
        try:
            log_context = "\n".join(
                f"- [{log.get(SCHEMA_TIMESTAMP)}] {log.get(SCHEMA_LEVEL)}: {log.get(SCHEMA_MESSAGE)} (Raw: {log.get(SCHEMA_RAW)})"
                for log in logs
            )

            prompt = (
                f"You are an expert system reliability assistant for Logara AI.\n"
                f"Based on the following relevant system logs, answer the user's natural language query.\n"
                f"Be concise, helpful, and technically accurate.\n\n"
                f"Query: \"{query}\"\n\n"
                f"Logs:\n{log_context}\n\n"
                f"Answer:"
            )

            url = f"{OLLAMA_BASE_URL}/api/generate"
            response = httpx.post(
                url,
                json={
                    "model": LOCAL_LLM_MODEL,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=60.0
            )
            if response.status_code == 200:
                answer = response.json().get("response")
        except Exception as e:
            logger.debug(f"Ollama natural language synthesis failed: {e}")
            answer = "Unable to contact Ollama for natural language summary. Please check your connection."

        return logs, answer
